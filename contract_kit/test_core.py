import copy
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from lxml import etree
import generate_demo as g
import salary_engine as salary
from decimal import Decimal


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.data = g.load_json(g.ROOT / "examples/employee_demo.json")
        self.policy = g.load_json(g.ROOT / "config/salary_policy_example.json")

    def test_supplied_salary_example(self):
        expected = {
            "base_wage": "5310000", "position_allowance": "690000",
            "employer_insurance": "1141650", "employer_union": "106200",
            "employee_insurance": "557550", "employee_union": "53100",
            "pit_withheld": "0", "gross_income": "6000000",
            "net_income": "5389350", "employer_total_cost": "7247850",
        }
        self.assertEqual(g.calculate_example(self.data, self.policy), expected)

    def test_employer_contributions_do_not_reduce_employee_net(self):
        changed = copy.deepcopy(self.policy)
        changed["rates"]["employer_insurance"] = "0.3"
        before = g.calculate_example(self.data, self.policy)
        after = g.calculate_example(self.data, changed)
        self.assertEqual(before["net_income"], after["net_income"])
        self.assertNotEqual(before["employer_total_cost"], after["employer_total_cost"])

    def test_missing_tax_is_not_zero(self):
        self.data["compensation"]["pit_withheld"] = None
        with self.assertRaises(ValueError):
            g.calculate_example(self.data, self.policy)

    def test_floating_point_input_is_rejected(self):
        self.data["compensation"]["salary_amount"] = 6000000.0
        with self.assertRaises(ValueError):
            g.calculate_example(self.data, self.policy)

    def test_real_issuance_is_not_claimed(self):
        self.data["demo_only"] = False
        with self.assertRaises(ValueError):
            g.build_context("dai_duong_xanh", self.data, self.policy)

    def test_split_run_replacement_preserves_neighbouring_text(self):
        p = etree.fromstring(
            ('<w:p xmlns:w="' + g.W + '"><w:r><w:t>A {{ emp</w:t></w:r>'
             '<w:r><w:t>loyee.full_name }} Z</w:t></w:r></w:p>').encode())
        combined = "".join(p.xpath(".//w:t/text()", namespaces=g.NS))
        m = g.TOKEN.search(combined)
        g.replace_span(p, m.start(), m.end(), "Tên & ký hiệu")
        self.assertEqual("".join(p.xpath(".//w:t/text()", namespaces=g.NS)),
                         "A Tên & ký hiệu Z")
        etree.fromstring(etree.tostring(p))

    def test_each_unit_populates_both_templates_without_other_tax_codes(self):
        units = g.load_json(g.ROOT / "config/units.json")["units"]
        with tempfile.TemporaryDirectory() as folder:
            for unit in units:
                context, _ = g.build_context(unit["unit_id"], self.data, self.policy)
                for template in (g.ROOT / "templates").glob("*.docx"):
                    output = Path(folder) / template.name
                    g.render_docx(template, output, context)
                    with ZipFile(output) as z:
                        root = etree.fromstring(z.read("word/document.xml"))
                        text = "".join(root.xpath("//w:t/text()", namespaces=g.NS))
                    self.assertIn(unit["tax_code"], text)
                    self.assertIn(unit["signatory_name"], text)
                    self.assertIn(self.data["employee"]["full_name"], text)
                    self.assertNotIn("{{", text)
                    for other in units:
                        if other["unit_id"] != unit["unit_id"]:
                            self.assertNotIn(other["tax_code"], text)

    def test_user_confirmed_position_base_wages(self):
        expected = {'principal':'7000000', 'preschool_teacher':'5310000',
                    'english_teacher':'5310000', 'nanny':'5310000',
                    'admissions_marketing':'5310000'}
        self.data['compensation']['salary_amount'] = '10000000'
        for position, base in expected.items():
            with self.subTest(position=position):
                self.data['job']['position_id'] = position
                self.assertEqual(g.calculate_example(self.data,self.policy)['base_wage'],base)

    def test_unknown_position_has_no_fallback_wage(self):
        self.data['job']['position_id'] = 'unknown'
        with self.assertRaises(ValueError):
            g.calculate_example(self.data,self.policy)

    def test_signature_is_single_manual_effective_date(self):
        self.data['signing_date'] = '2026-10-17'
        context,_ = g.build_context('dai_duong_xanh',self.data,self.policy)
        self.assertEqual(context['signing']['date_long'],'17 tháng 10 năm 2026')
        self.assertEqual(context['contract']['start_date'],'17/10/2026')
        self.assertEqual(context['employer']['tax_code'],'0318961728-002')
        # Appendix and responsibility dates have not been confirmed to sync.
        self.assertEqual(context['salary']['effective_from'],'01/08/2026')

    def test_missing_signing_date_does_not_default_to_today(self):
        for value in (None,''):
            with self.subTest(value=value):
                self.data['signing_date']=value
                with self.assertRaises(ValueError):
                    g.build_context('dai_duong_xanh',self.data,self.policy)

    def test_independent_contract_start_date_is_rejected(self):
        self.data['contract']['start_date']='2026-03-01'
        with self.assertRaises(ValueError):
            g.build_context('dai_duong_xanh',self.data,self.policy)

    def test_contract_cannot_end_before_manually_entered_date(self):
        self.data['signing_date']='2027-06-01'
        with self.assertRaises(ValueError):
            g.build_context('dai_duong_xanh',self.data,self.policy)

    def test_net_six_million_is_not_treated_as_gross(self):
        self.data['compensation']['salary_mode']='net'
        result=g.calculate_example(self.data,self.policy)
        self.assertEqual(result['net_income'],'6000000')
        self.assertEqual(result['gross_income'],'6610650')
        self.assertEqual(result['position_allowance'],'1300650')

    def test_net_round_trip_reproduces_original_sample(self):
        self.data['compensation']['salary_mode']='net'
        self.data['compensation']['salary_amount']='5389350'
        self.assertEqual(g.calculate_example(self.data,self.policy)['gross_income'],'6000000')

    def test_mode_is_required_and_cannot_be_guessed(self):
        for mode in (None,'','other'):
            with self.subTest(mode=mode):
                self.data['compensation']['salary_mode']=mode
                with self.assertRaises(ValueError):
                    g.calculate_example(self.data,self.policy)

    def test_amount_below_position_base_is_rejected(self):
        self.data['job']['position_id']='principal'
        with self.assertRaises(ValueError):
            g.calculate_example(self.data,self.policy)

    def test_reverse_search_recomputes_gross_dependent_deductions(self):
        observed=[]
        def toy_deductions(gross):
            # Invented arithmetic fixture, NOT a Vietnamese tax formula.
            observed.append(gross)
            tax=salary.round_vnd(max(Decimal(0),gross-Decimal('5000000'))*Decimal('0.1'))
            return dict(employee_insurance='0',employee_union='0',pit_withheld=tax,
                        employer_insurance='0',employer_union='0')
        result=salary.calculate_salary_terms('5310000','net','9000000',toy_deductions)
        self.assertEqual(result['gross_income'],Decimal('9444444'))
        self.assertEqual(result['net_income'],Decimal('9000000'))
        self.assertGreater(len(set(observed)),2)

    def test_residual_allowance_allocation_must_be_explicit(self):
        self.policy.pop('residual_allocation')
        with self.assertRaises(ValueError):
            g.calculate_example(self.data,self.policy)


if __name__ == "__main__":
    unittest.main()
