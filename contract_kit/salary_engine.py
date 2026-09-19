"""Integer-VND salary arithmetic. Supply a reviewed deduction function.

This module contains no statutory tax or insurance rates. Net-to-gross search
requires a deterministic, nondecreasing net(gross) function and an exact
whole-VND solution. Never present its caller's example policy as real payroll.
"""
from decimal import Decimal, ROUND_HALF_UP

MAX_VND = Decimal('1000000000000')
EMPLOYEE_ITEMS = ('employee_insurance', 'employee_union', 'pit_withheld')
EMPLOYER_ITEMS = ('employer_insurance', 'employer_union')


def decimal_input(value, label):
    if isinstance(value, (float, bool)) or value is None:
        raise ValueError(f'{label} phải là chuỗi thập phân, không dùng float')
    try:
        result = Decimal(value)
    except Exception as exc:
        raise ValueError(f'{label} không phải số hợp lệ') from exc
    if not result.is_finite() or result < 0:
        raise ValueError(f'{label} phải hữu hạn và không âm')
    return result


def whole_vnd(value, label):
    number = decimal_input(value, label)
    if number != number.to_integral_value() or number > MAX_VND:
        raise ValueError(f'{label} phải là số đồng nguyên trong phạm vi xử lý')
    return number


def round_vnd(value):
    return value.quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def gross_for_net(target, minimum_gross, evaluate_net):
    """Lower-bound search; recalculate deductions at EVERY candidate gross."""
    target = whole_vnd(target, 'salary_amount')
    minimum_gross = whole_vnd(minimum_gross, 'base_wage')
    if evaluate_net(minimum_gross) > target:
        raise ValueError('Net yêu cầu thấp hơn Net tại mức lương cơ bản')
    lo = int(minimum_gross)
    hi = min(int(MAX_VND), max(lo + 1, int(target) * 2 + lo))
    while evaluate_net(Decimal(hi)) < target:
        if hi == int(MAX_VND):
            raise ValueError('Không tìm được Gross trong phạm vi xử lý')
        hi = min(int(MAX_VND), hi * 2)
    while lo < hi:
        mid = (lo + hi) // 2
        if evaluate_net(Decimal(mid)) < target:
            lo = mid + 1
        else:
            hi = mid
    gross = Decimal(lo)
    if evaluate_net(gross) != target:
        raise ValueError('Không có Gross khớp Net chính xác theo quy tắc làm tròn')
    return gross


def calculate_salary_terms(base_wage, salary_mode, salary_amount,
                           deductions_for_gross):
    """Return terms; classify income above base separately from allowances."""
    base = whole_vnd(base_wage, 'base_wage')
    amount = whole_vnd(salary_amount, 'salary_amount')
    if base <= 0 or amount <= 0:
        raise ValueError('Lương cơ bản và lương thỏa thuận phải lớn hơn 0')
    if salary_mode not in ('gross', 'net'):
        raise ValueError('salary_mode phải là gross hoặc net')

    def evaluate(gross):
        raw = deductions_for_gross(gross)
        deductions = {}
        for key in EMPLOYEE_ITEMS + EMPLOYER_ITEMS:
            if key not in raw:
                raise ValueError(f'Thiếu khoản tính {key}; không tự coi là 0')
            deductions[key] = whole_vnd(raw[key], key)
        return gross - sum(deductions[k] for k in EMPLOYEE_ITEMS), deductions

    gross = amount if salary_mode == 'gross' else gross_for_net(
        amount, base, lambda value: evaluate(value)[0])
    if gross < base:
        raise ValueError('Gross thấp hơn lương cơ bản của vị trí đã chọn')
    net, deductions = evaluate(gross)
    if net < 0:
        raise ValueError('Thực nhận âm')
    if salary_mode == 'net' and net != amount:
        raise ValueError('Kết quả không khớp Net đã nhập')
    return {
        'base_wage': base,
        'income_above_base': gross - base,
        **deductions,
        'gross_income': gross,
        'net_income': net,
        'employer_total_cost': gross + sum(deductions[k] for k in EMPLOYER_ITEMS),
    }
