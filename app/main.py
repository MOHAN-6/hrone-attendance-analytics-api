"""Employee Attendance & Analytics API (HROne assignment, contract v2.0).



Run from the repository root: uvicorn app.main:app --port 8000

Configuration: MONGO_URI and MONGO_DB (environment variables override .env).

"""

from __future__ import annotations

from bson.timestamp import Timestamp



import math

import os

import re

from calendar import monthrange

from datetime import date, datetime, time, timedelta, timezone

from decimal import Decimal, ROUND_HALF_UP

from typing import Any, Optional, Literal



from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Query

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument

from pymongo.errors import DuplicateKeyError, PyMongoError

from pymongo.collection import Collection



load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

MONGO_DB = os.getenv("MONGO_DB", "attendance_db")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2500, tz_aware=False)

db = client[MONGO_DB]

employees: Collection = db["employees"]

attendance: Collection = db["attendance_logs"]



UTC = timezone.utc

IST = timezone(timedelta(hours=5, minutes=30))

PRESENCE = {"PRESENT", "WFH", "ON_DUTY"}

ALL_STATUSES = PRESENCE | {"ABSENT", "LEAVE"}

EPOCH_MIN = 100_000_000_000

EPOCH_MAX = 4_102_444_800_000



app = FastAPI(title="Employee Attendance & Analytics API", version="2.0.0")



# ---------------------------------------------------------------------------

# Common validation, time conversion, and serialization helpers

# ---------------------------------------------------------------------------

def create_indexes() -> None:

          """Idempotent indexes. The unique attendance key is the punch-in race guard."""

          employees.create_index([("emp_code", ASCENDING)], unique=True, name="uq_employee_code")

          employees.create_index([("department", ASCENDING), ("joined_on", ASCENDING)], name="ix_employee_department_joined")

          attendance.create_index([("emp_code", ASCENDING), ("date", ASCENDING)], unique=True, name="uq_attendance_employee_date")

          attendance.create_index([("date", DESCENDING), ("emp_code", ASCENDING)], name="ix_attendance_date_employee")

          attendance.create_index([("emp_code", ASCENDING), ("date", ASCENDING), ("status", ASCENDING)], name="ix_attendance_employee_date_status")

          attendance.create_index([("emp_code", ASCENDING), ("punch_in", DESCENDING)], name="ix_attendance_employee_punchin")

          attendance.create_index([("date", ASCENDING), ("late_minutes", DESCENDING), ("emp_code", ASCENDING)], name="ix_attendance_date_late_employee")





@app.on_event("startup")

def startup() -> None:

          # Do not fail app import when MongoDB is temporarily unavailable; /health reports 503.

          try:

                    create_indexes()

          except PyMongoError:

                    pass





def truncate_seconds(value: datetime) -> datetime:

          if value.tzinfo is None:

                    value = value.replace(tzinfo=UTC)

          return value.astimezone(UTC).replace(microsecond=0)





def epoch_to_dt(value: int | None, *, now_if_none: bool = False) -> datetime | None:

          if value is None:

                    return truncate_seconds(datetime.now(UTC)) if now_if_none else None

          # Pydantic validates this too; keeping this check makes helper use safe.

          if type(value) is not int or value < EPOCH_MIN or value > EPOCH_MAX:

                    raise HTTPException(422, "timestamp must be an integer epoch-millisecond value in range")

          return datetime.fromtimestamp(value / 1000, UTC).replace(microsecond=0)





def dt_to_epoch(value: datetime | None) -> int | None:

          if value is None:

                    return None

          if value.tzinfo is None:

                    value = value.replace(tzinfo=UTC)

          return int(value.timestamp() * 1000)





def stored_dt(value: datetime | None) -> datetime | None:

          """MongoDB/PyMongo stores and returns naive UTC datetimes by default."""

          return truncate_seconds(value).replace(tzinfo=None) if value is not None else None





def public_doc(doc: dict[str, Any], *, employee: bool = False) -> dict[str, Any]:

          out = {k: v for k, v in doc.items() if k not in {"_id", "id"}}

          if employee:

                    if isinstance(out.get("created_at"), datetime):

                              out["created_at"] = dt_to_epoch(out["created_at"])

                    return out

          for key in ("punch_in", "punch_out"):

                    if isinstance(out.get(key), datetime):

                              out[key] = dt_to_epoch(out[key])

                    elif key not in out:

                              out[key] = None

          out.setdefault("work_hours", None)

          out.setdefault("late_minutes", 0)

          out.setdefault("overtime_minutes", 0)

          out.setdefault("half_day", False)

          out.setdefault("history", [])

          for entry in out["history"]:

                    if isinstance(entry.get("at"), datetime):

                              entry["at"] = dt_to_epoch(entry["at"])

                    for field, pair in entry.get("changes", {}).items():

                              if field in {"punch_in", "punch_out"}:

                                        for side in ("from", "to"):

                                                  if isinstance(pair.get(side), datetime):

                                                            pair[side] = dt_to_epoch(pair[side])

          return out





def round_half_up(value: float | Decimal, places: int = 2) -> float:

          quantum = Decimal("1").scaleb(-places)

          return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))





def date_value(value: str, field_name: str = "date") -> date:

          try:

                    parsed = date.fromisoformat(value)

                    if parsed.isoformat() != value:

                              raise ValueError

                    return parsed

          except (ValueError, TypeError):

                    raise HTTPException(422, f"{field_name} must be YYYY-MM-DD")





def month_bounds(month: str) -> tuple[str, str, date, date]:

          if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month or ""):

                    raise HTTPException(422, "month must be YYYY-MM")

          year, mon = map(int, month.split("-"))

          last = monthrange(year, mon)[1]

          return f"{month}-01", f"{month}-{last:02d}", date(year, mon, 1), date(year, mon, last)





def working_days(start: date, end: date) -> int:

          if end < start:

                    return 0

          count = 0

          day = start

          while day <= end:

                    if day.weekday() < 5:

                              count += 1

                    day += timedelta(days=1)

          return count





def attendance_date_for(punch_in: datetime, shift_start: str, shift_end: str) -> date:

          local = punch_in.astimezone(IST)

          end_t = time.fromisoformat(shift_end)

          start_t = time.fromisoformat(shift_start)

          day = local.date()

          if end_t <= start_t and local.time().replace(tzinfo=None) < end_t:

                    day -= timedelta(days=1)

          return day





def shift_start_dt(day: date, shift_start: str) -> datetime:

          return datetime.combine(day, time.fromisoformat(shift_start), IST)





def shift_end_dt(day: date, shift_start: str, shift_end: str) -> datetime:

          end = datetime.combine(day, time.fromisoformat(shift_end), IST)

          if time.fromisoformat(shift_end) <= time.fromisoformat(shift_start):

                    end += timedelta(days=1)

          return end





def compute_late_minutes(punch_in: datetime, shift_start: str, attendance_day: date | None = None) -> int:

          local = punch_in.astimezone(IST)

          day = attendance_day or local.date()

          start = shift_start_dt(day, shift_start).astimezone(UTC)

          elapsed = (truncate_seconds(punch_in) - start).total_seconds()

          if elapsed <= 600:

                    return 0

          return max(0, math.floor(elapsed / 60))





def compute_work_hours(punch_in: datetime, punch_out: datetime) -> float:

          seconds = (truncate_seconds(punch_out) - truncate_seconds(punch_in)).total_seconds()

          return round_half_up(Decimal(str(seconds)) / Decimal(3600), 2)





def compute_overtime(punch_out: datetime, shift_start: str, shift_end: str, attendance_day: date) -> int:

          end = shift_end_dt(attendance_day, shift_start, shift_end).astimezone(UTC)

          minutes = math.floor((truncate_seconds(punch_out) - end).total_seconds() / 60)

          return minutes if minutes >= 30 else 0





def calculate_derived(status: str, punch_in: datetime | None, punch_out: datetime | None,

                                                           employee: dict[str, Any], day: date) -> dict[str, Any]:

          if status not in ALL_STATUSES:

                    raise HTTPException(422, "invalid status")

          if status in {"ABSENT", "LEAVE"}:

                    return {"punch_in": None, "punch_out": None, "work_hours": None,

                                        "late_minutes": 0, "overtime_minutes": 0, "half_day": False}

          if punch_in is None:

                    raise HTTPException(422, "presence status requires punch_in")

          if punch_in.astimezone(IST).date() != day and not (

                    time.fromisoformat(employee["shift_end"]) <= time.fromisoformat(employee["shift_start"])

                    and punch_in.astimezone(IST).time().replace(tzinfo=None) < time.fromisoformat(employee["shift_end"])

                    and punch_in.astimezone(IST).date() - timedelta(days=1) == day

          ):

                    raise HTTPException(422, "punch_in must fall on the record's attendance date")

          late = compute_late_minutes(punch_in, employee["shift_start"], day)

          if punch_out is None:

                    return {"punch_in": punch_in, "punch_out": None, "work_hours": None,

                                        "late_minutes": late, "overtime_minutes": 0, "half_day": False}

          elapsed = (punch_out - punch_in).total_seconds()

          if elapsed <= 0 or elapsed > 24 * 3600:

                    raise HTTPException(422, "punch_out must be after punch_in and within 24 hours")

          hours = compute_work_hours(punch_in, punch_out)

          overtime = compute_overtime(punch_out, employee["shift_start"], employee["shift_end"], day)

          return {"punch_in": punch_in, "punch_out": punch_out, "work_hours": hours,

                              "late_minutes": late, "overtime_minutes": overtime, "half_day": hours < 4.50}





def present_day_expression(date_field: str = "$date") -> dict[str, Any]:

          parsed = {"$dateFromString": {"dateString": date_field}}

          return {"$cond": [

                    {"$and": [

                              {"$in": ["$status", list(PRESENCE)]},

                              {"$lt": [{"$dayOfWeek": parsed}, 7]},

                              {"$gt": [{"$dayOfWeek": parsed}, 1]},

                    ]},

                    {"$cond": [{"$eq": ["$half_day", True]}, 0.5, 1.0]}, 0.0

          ]}

def json_safe(value: Any) -> Any:
    """Convert MongoDB explain output to JSON-serializable Python values."""
    # BSON Timestamp must be handled explicitly before returning unknown values.
    if isinstance(value, Timestamp) or (
        value.__class__.__name__ == "Timestamp"
        and hasattr(value, "time")
        and hasattr(value, "inc")
    ):
        return {"time": int(value.time), "inc": int(value.inc)}

    if isinstance(value, datetime):
        return dt_to_epoch(value)

    if isinstance(value, dict):
        return {
            str(k): json_safe(v)
            for k, v in value.items()
            if k != "_id"
        }

    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]

    # Convert BSON-specific values that may appear in explain output.
    class_name = value.__class__.__name__
    if class_name == "ObjectId":
        return str(value)
    if class_name == "Decimal128":
        return float(value.to_decimal())
    if class_name == "Binary":
        return value.hex()
    if class_name == "Regex":
        return {"pattern": value.pattern, "flags": value.flags}

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)

    # Never leak unsupported objects to FastAPI's JSON encoder.
    if hasattr(value, "__int__"):
        try:
            return int(value)
        except (TypeError, ValueError, OverflowError):
            pass
    return str(value)


class APIModel(BaseModel):

          model_config = ConfigDict(extra="ignore")





def validate_epoch(value: Any) -> Any:

          if value is None:

                    return value

          if type(value) is not int or value < EPOCH_MIN or value > EPOCH_MAX:

                    raise ValueError("must be an integer epoch-millisecond timestamp in the supported range")

          return value





class EmployeeIn(APIModel):

          emp_code: str = Field(pattern=r"^EMP\d{4,6}$")

          name: str = Field(min_length=1, max_length=100)

          email: str = Field(max_length=120, pattern=r"^[^@\s]+@[^@\s]+**\.**[^@\s]+$")

          department: str = Field(min_length=1, max_length=50)

          shift_start: str = Field(default="09:30", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")

          shift_end: str = Field(default="18:30", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")

          joined_on: str



          @field_validator("joined_on")

          @classmethod

          def valid_joined_on(cls, value: str) -> str:

                    try:

                              if date.fromisoformat(value).isoformat() != value: raise ValueError

                    except ValueError:

                              raise ValueError("joined_on must be YYYY-MM-DD")

                    return value



          @model_validator(mode="after")

          def different_shift_times(self):

                    if self.shift_start == self.shift_end:

                              raise ValueError("shift_start must differ from shift_end")

                    return self





class PunchInIn(APIModel):

          emp_code: str

          punched_at: Optional[StrictInt] = None

          status: Literal["PRESENT", "WFH", "ON_DUTY"] = "PRESENT"

          @field_validator("punched_at")

          @classmethod

          def valid_punched_at(cls, value): return validate_epoch(value)





class PunchOutIn(APIModel):

          emp_code: str

          punched_at: Optional[StrictInt] = None

          @field_validator("punched_at")

          @classmethod

          def valid_punched_at(cls, value): return validate_epoch(value)





class RegularizeIn(APIModel):

          status: Optional[Literal["PRESENT", "ABSENT", "LEAVE", "WFH", "ON_DUTY"]] = None

          punch_in: Optional[StrictInt] = None

          punch_out: Optional[StrictInt] = None

          reason: str = Field(min_length=5, max_length=200)

          regularized_by: str = Field(min_length=1, max_length=50)

          @field_validator("punch_in", "punch_out")

          @classmethod

          def valid_times(cls, value): return validate_epoch(value)





# ---------------------------------------------------------------------------

# Basic endpoints

# ---------------------------------------------------------------------------

@app.get("/health")

def health():

          try:

                    client.admin.command("ping")

                    return {"status": "ok"}

          except PyMongoError:

                    raise HTTPException(503, "MongoDB unavailable")





@app.post("/employees", status_code=201)

def create_employee(body: EmployeeIn):

          doc = body.model_dump()

          doc["created_at"] = stored_dt(truncate_seconds(datetime.now(UTC)))

          try:

                    employees.insert_one(doc)

          except DuplicateKeyError:

                    raise HTTPException(409, "emp_code already exists")

          return public_doc(doc, employee=True)





@app.get("/employees")

def list_employees(department: Optional[str] = None, page: int = Query(1, ge=1),

                                                 page_size: int = Query(20, ge=1, le=100)):

          query = {"department": department} if department is not None else {}

          total = employees.count_documents(query)

          docs = employees.find(query, {"_id": 0}).sort("emp_code", ASCENDING).skip((page - 1) * page_size).limit(page_size)

          return {"items": [public_doc(d, employee=True) for d in docs], "total": total, "page": page, "page_size": page_size}





@app.post("/attendance/punch-in", status_code=201)

def punch_in(body: PunchInIn):

          emp = employees.find_one({"emp_code": body.emp_code})

          if not emp:

                    raise HTTPException(404, "unknown employee")

          ts = epoch_to_dt(body.punched_at, now_if_none=True)

          day = attendance_date_for(ts, emp["shift_start"], emp["shift_end"])

          late = compute_late_minutes(ts, emp["shift_start"], day)

          doc = {"emp_code": body.emp_code, "date": day.isoformat(), "status": body.status,

                             "punch_in": stored_dt(ts), "punch_out": None, "work_hours": None,

                             "late_minutes": late, "overtime_minutes": 0, "half_day": False, "history": []}

          try:

                    attendance.insert_one(doc)

          except DuplicateKeyError:

                    raise HTTPException(409, "already punched in for this date")

          return public_doc(doc)





@app.post("/attendance/punch-out")

def punch_out(body: PunchOutIn):

          emp = employees.find_one({"emp_code": body.emp_code})

          if not emp:

                    raise HTTPException(404, "unknown employee")

          ts = epoch_to_dt(body.punched_at, now_if_none=True)

          # Select the most recent shift already started at or before the supplied instant.

          rec = attendance.find_one({"emp_code": body.emp_code, "punch_in": {"$ne": None, "$lte": stored_dt(ts)}},

                                                                           sort=[("punch_in", DESCENDING)])

          if not rec:

                    raise HTTPException(404, "no punch-in found")

          if rec.get("punch_out") is not None:

                    raise HTTPException(409, "record already punched out")

          punch_in_dt = rec["punch_in"].replace(tzinfo=UTC)

          elapsed = (ts - punch_in_dt).total_seconds()

          if elapsed <= 0 or elapsed > 86400:

                    raise HTTPException(422, "punched_at must be after punch_in and within 24 hours")

          day = date_value(rec["date"])

          derived = calculate_derived(rec["status"], punch_in_dt, ts, emp, day)

          # Compare-and-set makes concurrent punch-outs atomic: one update succeeds.

          updated = attendance.find_one_and_update(

                    {"_id": rec["_id"], "punch_out": None},

                    {"$set": {"punch_out": stored_dt(ts), "work_hours": derived["work_hours"],

                                                 "overtime_minutes": derived["overtime_minutes"], "half_day": derived["half_day"]}},

                    return_document=ReturnDocument.AFTER)

          if updated is None:

                    raise HTTPException(409, "record already punched out")

          return public_doc(updated)





@app.get("/attendance")

def list_attendance(emp_code: Optional[str] = None, date_from: Optional[str] = None,

                                                  date_to: Optional[str] = None, status: Optional[str] = None,

                                                  page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):

          query: dict[str, Any] = {}

          if emp_code is not None: query["emp_code"] = emp_code

          if date_from is not None:

                    date_value(date_from, "date_from")

                    query.setdefault("date", {})["$gte"] = date_from

          if date_to is not None:

                    date_value(date_to, "date_to")

                    query.setdefault("date", {})["$lte"] = date_to

          if date_from and date_to and date_from > date_to:

                    raise HTTPException(422, "date_from must be <= date_to")

          if status is not None:

                    if status not in ALL_STATUSES: raise HTTPException(422, "invalid status")

                    query["status"] = status

          total = attendance.count_documents(query)

          docs = attendance.find(query).sort([("date", DESCENDING), ("emp_code", ASCENDING)]).skip((page - 1) * page_size).limit(page_size)

          return {"items": [public_doc(d) for d in docs], "total": total, "page": page, "page_size": page_size}





# ---------------------------------------------------------------------------

# Manual correction with atomic history append and optimistic concurrency

# ---------------------------------------------------------------------------

def same_field_filter(doc: dict[str, Any], field: str) -> dict[str, Any]:

          if field not in doc:

                    return {field: {"$exists": False}}

          return {field: doc[field]}





@app.patch("/attendance/{emp_code}/{date}")

def regularize_attendance(emp_code: str, date: str, body: RegularizeIn):

          try: day = date_value(date)

          except HTTPException: raise

          emp = employees.find_one({"emp_code": emp_code})

          if not emp: raise HTTPException(404, "unknown employee")

          rec = attendance.find_one({"emp_code": emp_code, "date": date})

          if not rec: raise HTTPException(404, "attendance record not found")

          patch = body.model_dump(exclude_unset=True)

          requested_status = patch.get("status", rec.get("status"))

          if requested_status in {"ABSENT", "LEAVE"} and (patch.get("punch_in") is not None or patch.get("punch_out") is not None):

                    raise HTTPException(422, "ABSENT/LEAVE cannot be supplied with punch times")

          new_in = epoch_to_dt(patch["punch_in"]) if "punch_in" in patch else (rec.get("punch_in").replace(tzinfo=UTC) if rec.get("punch_in") else None)

          new_out = epoch_to_dt(patch["punch_out"]) if "punch_out" in patch else (rec.get("punch_out").replace(tzinfo=UTC) if rec.get("punch_out") else None)

          if requested_status in {"ABSENT", "LEAVE"}:

                    new_in = new_out = None

          derived = calculate_derived(requested_status, new_in, new_out, emp, day)

          old_values = {"status": rec.get("status"), "punch_in": rec.get("punch_in"), "punch_out": rec.get("punch_out"),

                                             "work_hours": rec.get("work_hours"), "late_minutes": rec.get("late_minutes", 0),

                                             "overtime_minutes": rec.get("overtime_minutes", 0), "half_day": rec.get("half_day", False)}

          new_values = {"status": requested_status, **derived}

          changes: dict[str, Any] = {}

          for field in ("status", "punch_in", "punch_out", "work_hours", "late_minutes", "overtime_minutes", "half_day"):

                    old = old_values.get(field)

                    new = new_values.get(field)

                    # Normalize stored BSON datetimes and new UTC-aware datetimes for comparison.

                    if field in {"punch_in", "punch_out"}:

                              old_cmp = truncate_seconds(old.replace(tzinfo=UTC)) if isinstance(old, datetime) else None

                              new_cmp = truncate_seconds(new) if isinstance(new, datetime) else None

                              changed = old_cmp != new_cmp

                              old_api, new_api = dt_to_epoch(old_cmp), dt_to_epoch(new_cmp)

                              old_store = stored_dt(old_cmp) if old_cmp is not None else None

                              new_store = stored_dt(new_cmp) if new_cmp is not None else None

                    else:

                              changed = old != new

                              old_api, new_api = old, new

                              old_store, new_store = old, new

                    if changed: changes[field] = {"from": old_store, "to": new_store}

          if not changes:

                    raise HTTPException(422, "request does not change the record")

          at = truncate_seconds(datetime.now(UTC))

          history_entry = {"at": stored_dt(at), "by": body.regularized_by, "reason": body.reason, "changes": changes}

          # Match the current state as a compare-and-set guard; $push is atomic and never overwrites history.

          filter_parts: list[dict[str, Any]] = [{"_id": rec["_id"]}, same_field_filter(rec, "history")]

          for field in ("status", "punch_in", "punch_out", "work_hours", "late_minutes", "overtime_minutes", "half_day"):

                    filter_parts.append(same_field_filter(rec, field))

          set_values = {"status": requested_status, "punch_in": stored_dt(derived["punch_in"]),

                                             "punch_out": stored_dt(derived["punch_out"]), "work_hours": derived["work_hours"],

                                             "late_minutes": derived["late_minutes"], "overtime_minutes": derived["overtime_minutes"],

                                             "half_day": derived["half_day"]}

          updated = attendance.find_one_and_update({"$and": filter_parts}, {"$set": set_values, "$push": {"history": history_entry}},

                                                                                                                   return_document=ReturnDocument.AFTER)

          if updated is None: raise HTTPException(409, "record changed concurrently; retry the correction")

          return public_doc(updated)





# ---------------------------------------------------------------------------

# Analytics pipelines

# ---------------------------------------------------------------------------

def monthly_pipeline(emp_code: str, first: str, last: str) -> list[dict[str, Any]]:

          return [

                    {"$match": {"emp_code": emp_code, "date": {"$gte": first, "$lte": last}}},

                    {"$addFields": {"_parsed_date": {"$dateFromString": {"dateString": "$date"}}}},

                    {"$group": {"_id": None,

                              "present_days": {"$sum": {"$cond": [

                                        {"$and": [{"$in": ["$status", list(PRESENCE)]},

                                                                 {"$gte": [{"$dayOfWeek": "$_parsed_date"}, 2]},

                                                                 {"$lte": [{"$dayOfWeek": "$_parsed_date"}, 6]}]},

                                        {"$cond": [{"$eq": ["$half_day", True]}, 0.5, 1.0]}, 0.0]}},

                              "leave_days": {"$sum": {"$cond": [{"$eq": ["$status", "LEAVE"]}, 1, 0]}},

                              "late_count": {"$sum": {"$cond": [{"$gt": [{"$ifNull": ["$late_minutes", 0]}, 0]}, 1, 0]}},

                              "total_late_minutes": {"$sum": {"$ifNull": ["$late_minutes", 0]}},

                              "total_overtime_minutes": {"$sum": {"$ifNull": ["$overtime_minutes", 0]}}}},

                    {"$project": {"_id": 0, "present_days": 1, "leave_days": 1, "late_count": 1,

                                                       "total_late_minutes": 1, "total_overtime_minutes": 1}}

          ]





@app.get("/analytics/employees/{emp_code}/monthly")

def employee_monthly(emp_code: str, month: str):

          emp = employees.find_one({"emp_code": emp_code}, {"_id": 0, "emp_code": 1, "joined_on": 1})

          if not emp: raise HTTPException(404, "unknown employee")

          first_s, last_s, first_d, last_d = month_bounds(month)

          start = max(first_d, date_value(emp["joined_on"], "joined_on"))

          workdays = working_days(start, last_d) if start <= last_d else 0

          rows = list(attendance.aggregate(monthly_pipeline(emp_code, first_s, last_s), allowDiskUse=True))

          result = rows[0] if rows else {"present_days": 0.0, "leave_days": 0, "late_count": 0, "total_late_minutes": 0, "total_overtime_minutes": 0}

          present = round_half_up(result.get("present_days", 0.0), 2)

          pct = round_half_up(Decimal(str(present)) / Decimal(workdays) * 100, 4) if workdays else None

          return {"emp_code": emp_code, "month": month, "working_days": workdays, "present_days": present,

                              "leave_days": int(result.get("leave_days", 0)), "late_count": int(result.get("late_count", 0)),

                              "total_late_minutes": int(result.get("total_late_minutes", 0)),

                              "total_overtime_minutes": int(result.get("total_overtime_minutes", 0)), "attendance_pct": pct}





def department_summary_pipeline(first: str, last: str, department: str | None = None) -> list[dict[str, Any]]:

          match: dict[str, Any] = {"joined_on": {"$lte": last}}

          if department is not None: match["department"] = department

          return [

                    {"$match": match},

                    {"$lookup": {"from": "attendance_logs", "let": {"code": "$emp_code"}, "pipeline": [

                              {"$match": {"$expr": {"$and": [{"$eq": ["$emp_code", "$$code"]},

                                                                                                                   {"$gte": ["$date", first]}, {"$lte": ["$date", last]}]}}},

                              {"$addFields": {"_parsed_date": {"$dateFromString": {"dateString": "$date"}}}},

                              {"$addFields": {"_weekday": {"$and": [{"$gte": [{"$dayOfWeek": "$_parsed_date"}, 2]}, {"$lte": [{"$dayOfWeek": "$_parsed_date"}, 6]}]}}},

                              {"$group": {"_id": None,

                                        "present_days": {"$sum": {"$cond": [{"$and": [{"$in": ["$status", list(PRESENCE)]}, "$_weekday"]}, {"$cond": [{"$eq": ["$half_day", True]}, 0.5, 1.0]}, 0.0]}},

                                        "hours_sum": {"$sum": {"$cond": [{"$and": [{"$in": ["$status", list(PRESENCE)]}, {"$ne": ["$work_hours", None]}]}, "$work_hours", 0]}},

                                        "hours_count": {"$sum": {"$cond": [{"$and": [{"$in": ["$status", list(PRESENCE)]}, {"$ne": ["$work_hours", None]}]}, 1, 0]}},

                                        "late_count": {"$sum": {"$cond": [{"$gt": [{"$ifNull": ["$late_minutes", 0]}, 0]}, 1, 0]}},

                                        "total_late_minutes": {"$sum": {"$ifNull": ["$late_minutes", 0]}},

                                        "leave_count": {"$sum": {"$cond": [{"$eq": ["$status", "LEAVE"]}, 1, 0]}},

                                        "on_duty_count": {"$sum": {"$cond": [{"$eq": ["$status", "ON_DUTY"]}, 1, 0]}}}}

                    ], "as": "metrics"}},

                    {"$unwind": {"path": "$metrics", "preserveNullAndEmptyArrays": True}},

                    {"$group": {"_id": "$department", "headcount": {"$sum": 1},

                              "present_days": {"$sum": {"$ifNull": ["$metrics.present_days", 0]}},

                              "hours_sum": {"$sum": {"$ifNull": ["$metrics.hours_sum", 0]}},

                              "hours_count": {"$sum": {"$ifNull": ["$metrics.hours_count", 0]}},

                              "late_count": {"$sum": {"$ifNull": ["$metrics.late_count", 0]}},

                              "total_late_minutes": {"$sum": {"$ifNull": ["$metrics.total_late_minutes", 0]}},

                              "leave_count": {"$sum": {"$ifNull": ["$metrics.leave_count", 0]}},

                              "on_duty_count": {"$sum": {"$ifNull": ["$metrics.on_duty_count", 0]}}}},

                    {"$match": {"headcount": {"$gt": 0}}},

                    {"$project": {"_id": 0, "department": "$_id", "headcount": 1, "present_days": 1,

                              "avg_work_hours": {"$cond": [{"$gt": ["$hours_count", 0]}, {"$divide": ["$hours_sum", "$hours_count"]}, None]},

                              "late_count": 1, "total_late_minutes": 1, "leave_count": 1, "on_duty_count": 1}},

                    {"$sort": {"department": 1}}

          ]





@app.get("/analytics/departments/summary")

def department_summary(month: str, department: Optional[str] = None):

          first, last, _, _ = month_bounds(month)

          result = list(employees.aggregate(department_summary_pipeline(first, last, department), allowDiskUse=True))

          for row in result:

                    row["present_days"] = round_half_up(row.get("present_days", 0), 2)

                    if row.get("avg_work_hours") is not None: row["avg_work_hours"] = round_half_up(row["avg_work_hours"], 2)

                    for key in ("headcount", "late_count", "total_late_minutes", "leave_count", "on_duty_count"):

                              row[key] = int(row.get(key, 0))

          return result





def leaderboard_pipeline(first: str, last: str, limit: int, department: str | None = None) -> list[dict[str, Any]]:

          pipeline: list[dict[str, Any]] = [

                    {"$match": {"date": {"$gte": first, "$lte": last}, "late_minutes": {"$gt": 0}}},

                    {"$group": {"_id": "$emp_code", "total_late_minutes": {"$sum": "$late_minutes"}}},

                    {"$lookup": {"from": "employees", "localField": "_id", "foreignField": "emp_code", "as": "employee"}},

                    {"$unwind": "$employee"},

          ]

          if department is not None: pipeline.append({"$match": {"employee.department": department}})

          pipeline += [

                    {"$set": {"emp_code": "$_id", "name": "$employee.name", "department": "$employee.department"}},

                    {"$setWindowFields": {"sortBy": {"total_late_minutes": -1}, "output": {"rank": {"$rank": {}}}}},

                    {"$match": {"rank": {"$lte": limit}}},

                    {"$sort": {"total_late_minutes": -1, "emp_code": 1}},

                    {"$project": {"_id": 0, "emp_code": 1, "name": 1, "department": 1, "total_late_minutes": 1, "rank": 1}}

          ]

          return pipeline





@app.get("/analytics/leaderboard/late")

def late_leaderboard(month: str, limit: int = Query(10, ge=1, le=50), department: Optional[str] = None):

          first, last, _, _ = month_bounds(month)

          return list(attendance.aggregate(leaderboard_pipeline(first, last, limit, department), allowDiskUse=True))





def trend_pipeline(department: str, from_day: date, to_day: date) -> list[dict[str, Any]]:

          # Seed one row, then let MongoDB densify the date range. No Python date-by-date loop.

          start_dt = datetime.combine(from_day, time.min, IST).astimezone(UTC).replace(tzinfo=None)

          end_dt = datetime.combine(to_day + timedelta(days=1), time.min, IST).astimezone(UTC).replace(tzinfo=None)

          return [

                    {"$documents": [{"day": start_dt}]},

                    {"$densify": {"field": "day", "range": {"step": 1, "unit": "day", "bounds": [start_dt, end_dt]}}},

                    {"$lookup": {"from": "employees", "let": {"day": "$day"}, "pipeline": [

                              {"$match": {"department": department}},

                              {"$match": {"$expr": {"$lte": ["$joined_on", {"$dateToString": {"date": "$$day", "format": "%Y-%m-%d", "timezone": "+05:30"}}]}}},

                              {"$project": {"_id": 0, "emp_code": 1}}

                    ], "as": "eligible_employees"}},

                    {"$set": {"_employee_codes": {"$map": {"input": "$eligible_employees", "as": "e", "in": "$$e.emp_code"}},

                                                 "date_string": {"$dateToString": {"date": "$day", "format": "%Y-%m-%d", "timezone": "+05:30"}},

                                                 "is_working_day": {"$and": [{"$gte": [{"$dayOfWeek": "$day"}, 2]}, {"$lte": [{"$dayOfWeek": "$day"}, 6]}]}}},

                    {"$lookup": {"from": "attendance_logs", "let": {"day_string": "$date_string", "codes": "$_employee_codes"}, "pipeline": [

                              {"$match": {"$expr": {"$and": [{"$eq": ["$date", "$$day_string"]}, {"$in": ["$emp_code", "$$codes"]}]}}},

                              {"$group": {"_id": None,

                                        "present_count": {"$sum": {"$cond": [{"$in": ["$status", list(PRESENCE)]}, {"$cond": [{"$eq": ["$half_day", True]}, 0.5, 1.0]}, 0.0]}},

                                        "late_count": {"$sum": {"$cond": [{"$gt": [{"$ifNull": ["$late_minutes", 0]}, 0]}, 1, 0]}}}}

                    ], "as": "day_metrics"}},

                    {"$set": {"headcount": {"$size": "$_employee_codes"},

                                                 "present_count": {"$ifNull": [{"$arrayElemAt": ["$day_metrics.present_count", 0]}, 0]},

                                                 "late_count": {"$ifNull": [{"$arrayElemAt": ["$day_metrics.late_count", 0]}, 0]}}},

                    {"$set": {"attendance_rate": {"$cond": [

                              {"$and": ["$is_working_day", {"$gt": ["$headcount", 0]}]},

                              {"$divide": [{"$floor": {"$add": [{"$multiply": [{"$divide": ["$present_count", "$headcount"]}, 10000]}, 0.5]}}, 10000]}, None]}}},

                    {"$setWindowFields": {"sortBy": {"day": 1}, "output": {"_moving_raw": {"$avg": "$attendance_rate", "window": {"documents": [-6, 0]}}}}},

                    {"$project": {"_id": 0, "date": "$date_string", "is_working_day": 1, "headcount": 1, "present_count": 1,

                                                           "late_count": 1, "attendance_rate": 1,

                                                           "moving_avg_7d": {"$cond": [{"$eq": ["$_moving_raw", None]}, None,

                                                                     {"$divide": [{"$floor": {"$add": [{"$multiply": ["$_moving_raw", 10000]}, 0.5]}}, 10000]}]}}},

                    {"$sort": {"date": 1}}

          ]





@app.get("/analytics/departments/{department}/trend")

def department_trend(department: str, from_date: str = Query(alias="from"), to_date: str = Query(alias="to")):

          start = date_value(from_date, "from")

          end = date_value(to_date, "to")

          if end < start: raise HTTPException(422, "to must be on or after from")

          if (end - start).days + 1 > 92: raise HTTPException(422, "date range cannot exceed 92 days")

          if employees.count_documents({"department": department}) == 0:

                    raise HTTPException(404, "unknown department")

          # Database-level $documents + $densify pipeline is supported by MongoDB 6.0+.

          return list(db.aggregate(trend_pipeline(department, start, end), allowDiskUse=True))





# ---------------------------------------------------------------------------

# Explain endpoint: same query/pipeline builders as the real endpoints

# ---------------------------------------------------------------------------

def explain_aggregate(collection_name: str | int, pipeline: list[dict[str, Any]]) -> dict[str, Any]:

          command = {"aggregate": collection_name, "pipeline": pipeline, "cursor": {}, "allowDiskUse": True}

          return db.command({"explain": command, "verbosity": "executionStats"})





@app.get("/admin/explain/{endpoint}")

def explain_endpoint(endpoint: str, emp_code: Optional[str] = None, month: Optional[str] = None,

                                                      department: Optional[str] = None, limit: int = Query(10, ge=1, le=50),

                                                      date_from: Optional[str] = None, date_to: Optional[str] = None,

                                                      status: Optional[str] = None, from_date: Optional[str] = Query(None, alias="from"),

                                                      to_date: Optional[str] = Query(None, alias="to"), page: int = Query(1, ge=1),

                                                      page_size: int = Query(20, ge=1, le=100)):

          if endpoint == "attendance_list":

                    q: dict[str, Any] = {}

                    if emp_code is not None: q["emp_code"] = emp_code

                    if date_from:

                              date_value(date_from, "date_from"); q.setdefault("date", {})["$gte"] = date_from

                    if date_to:

                              date_value(date_to, "date_to"); q.setdefault("date", {})["$lte"] = date_to

                    if date_from and date_to and date_from > date_to: raise HTTPException(422, "date_from must be <= date_to")

                    if status:

                              if status not in ALL_STATUSES: raise HTTPException(422, "invalid status")

                              q["status"] = status

                    pipeline = [{"$match": q}, {"$sort": {"date": -1, "emp_code": 1}}, {"$skip": (page - 1) * page_size}, {"$limit": page_size}]

                    coll: str | int = "attendance_logs"

          elif endpoint == "employee_monthly":

                    if not emp_code or not month: raise HTTPException(422, "emp_code and month are required")

                    first, last, _, _ = month_bounds(month)

                    pipeline = monthly_pipeline(emp_code, first, last); coll = "attendance_logs"

          elif endpoint == "department_summary":

                    if not month: raise HTTPException(422, "month is required")

                    first, last, _, _ = month_bounds(month)

                    pipeline = department_summary_pipeline(first, last, department); coll = "employees"

          elif endpoint == "late_leaderboard":

                    if not month: raise HTTPException(422, "month is required")

                    first, last, _, _ = month_bounds(month)

                    pipeline = leaderboard_pipeline(first, last, limit, department); coll = "attendance_logs"

          elif endpoint == "department_trend":

                    if not department or not from_date or not to_date: raise HTTPException(422, "department, from and to are required")

                    start, end = date_value(from_date, "from"), date_value(to_date, "to")

                    if end < start or (end - start).days + 1 > 92: raise HTTPException(422, "invalid trend date range")

                    pipeline = trend_pipeline(department, start, end); coll = 1

          else:

                    raise HTTPException(422, "endpoint must be one of attendance_list, employee_monthly, department_summary, late_leaderboard, department_trend")

          try:

                    explanation = explain_aggregate(coll, pipeline)

          except PyMongoError as exc:

                    raise HTTPException(503, f"MongoDB explain failed: {exc.__class__.__name__}")

          return {"endpoint": endpoint, "collection": "database" if coll == 1 else coll, "explain": json_safe(explanation)}
