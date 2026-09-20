"""Định nghĩa dữ liệu đầu vào của API.

Các ràng buộc ở đây chỉ kiểm tra hình thức. Quy tắc nghiệp vụ (mức lương
theo vị trí, ngày ký bằng ngày hiệu lực, chế độ Gross/Net) vẫn do
contract_kit quyết định.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Money = Annotated[str, Field(pattern=r"^\d{1,12}$")]
Text = Annotated[str, Field(min_length=1, max_length=500)]
LongText = Annotated[str, Field(min_length=1, max_length=2000)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Employee(Strict):
    full_name: Text
    code: Text
    birth_date: date
    gender: Text
    nationality: Text
    identity_number: Annotated[str, Field(pattern=r"^\d{9,12}$")]
    identity_issue_date: date
    identity_issuer: Text
    permanent_address: LongText


class ProbationEmployee(Employee):
    """Hợp đồng thử việc có thêm dòng Quê quán mà hợp đồng chính thức không có."""

    hometown: Text


class Job(Strict):
    position_id: Text


class Contract(Strict):
    type_term_text: LongText
    end_date: date


class Period(Strict):
    effective_from: date
    effective_to: date


class Responsibility(Strict):
    commitment_from: date
    commitment_to: date
    liability_from: date
    liability_to: date


class Compensation(Strict):
    insurance_base: Money
    employer_union_base: Money
    employee_union_base: Money
    salary_mode: Literal["gross", "net"]
    salary_amount: Money

    @field_validator("salary_amount")
    @classmethod
    def positive(cls, value: str) -> str:
        if Decimal(value) <= 0:
            raise ValueError("Số tiền lương phải lớn hơn 0")
        return value


class WorkSchedule(Strict):
    weekdays_label: LongText
    weekday_morning: LongText
    weekday_afternoon: LongText
    saturday_label: LongText
    saturday_morning: LongText
    saturday_afternoon: LongText
    weekday_lunch: LongText
    saturday_lunch: LongText


class Payment(Strict):
    window_text: LongText


class ContractRequest(Strict):
    """Một bộ dữ liệu đủ để dựng hợp đồng, phụ lục và thỏa thuận."""

    unit_id: Text
    employee: Employee
    job: Job
    signing_date: date
    contract: Contract
    salary_period: Period
    responsibility: Responsibility
    compensation: Compensation
    work_schedule: WorkSchedule
    payment: Payment

    def to_kit_payload(self) -> dict:
        """Chuyển sang đúng định dạng schema 1.2 mà contract_kit yêu cầu."""
        payload = self.model_dump(mode="json")
        payload.pop("unit_id")
        payload["schema_version"] = "1.2"
        # Phần lõi chỉ chấp nhận dữ liệu minh họa. Khi nào có luồng phát hành
        # chính thức thì mới bỏ cờ này.
        payload["demo_only"] = True
        return payload


class ProbationJob(Strict):
    position_id: Text
    department: Text
    supervisor_name: Text


class Probation(Strict):
    start_date: date
    end_date: date
    full_gross: Money
    # Nhà trường đang dùng 85%; để sửa được vì có thể khác theo từng người.
    rate_percent: Annotated[str, Field(pattern=r"^\d{1,3}(\.\d{1,2})?$")]
    work_hours: Text
    rest_hours: Text

    @field_validator("full_gross")
    @classmethod
    def duong(cls, value: str) -> str:
        if Decimal(value) <= 0:
            raise ValueError("Lương chính thức phải lớn hơn 0")
        return value


class ProbationRequest(Strict):
    """Hợp đồng thử việc: một tờ, không phụ lục, không thỏa thuận.

    Thời gian thử việc chưa hưởng chế độ bảo hiểm và công đoàn nên không
    có phần khấu trừ; vì vậy đầu vào không kèm compensation.
    """

    unit_id: Text
    employee: ProbationEmployee
    job: ProbationJob
    signing_date: date
    probation: Probation
    payment: Payment

    def to_kit_payload(self) -> dict:
        payload = self.model_dump(mode="json")
        payload.pop("unit_id")
        return payload


class AddressRequest(Strict):
    """Địa chỉ cần viết lại cho đầy đủ."""

    address: Annotated[str, Field(max_length=2000)]


class SalaryRequest(Strict):
    """Chỉ những gì cần để tính lương, không đòi hồ sơ đầy đủ."""

    position_id: Text
    compensation: Compensation

    def to_kit_payload(self) -> dict:
        return self.compensation.model_dump(mode="json")


class CalculationResponse(BaseModel):
    demo_only: bool
    unit_id: str
    calculation: dict[str, str]
    policy_status: str
