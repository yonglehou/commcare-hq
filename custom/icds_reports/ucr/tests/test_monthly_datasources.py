import os
import mock
from datetime import datetime, timedelta
from xml.etree import ElementTree

from django.test import TestCase
from corehq.util.test_utils import TestFileMixin
from corehq.form_processor.tests.utils import FormProcessorTestUtils
from corehq.apps.receiverwrapper.util import submit_form_locally

from corehq.apps.userreports.sql import IndicatorSqlAdapter
from corehq.apps.userreports.models import StaticDataSourceConfiguration
from corehq.apps.userreports.tasks import rebuild_indicators
from casexml.apps.case.const import CASE_INDEX_CHILD
from casexml.apps.case.mock import CaseFactory, CaseStructure, CaseIndex

XMNLS_BP_FORM="http://openrosa.org/formdesigner/2864010F-B1B1-4711-8C59-D5B2B81D65DB"
XMLNS_THR_FORM="http://openrosa.org/formdesigner/F1B73934-8B70-4CEE-B462-3E4C81F80E4A"


class BaseICDSDatasourceTest(TestCase, TestFileMixin):
    dependent_apps = ['corehq.apps.domain', 'corehq.apps.case']
    file_path = ('data_sources', )
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
    _call_center_domain_mock = mock.patch(
        'corehq.apps.callcenter.data_source.call_center_data_source_configuration_provider'
    )
    datasource_filename = ''

    @classmethod
    def setUpClass(cls):
        super(BaseICDSDatasourceTest, cls).setUpClass()
        cls._call_center_domain_mock.start()
        cls.static_datasource = StaticDataSourceConfiguration.wrap(
            cls.get_json(cls.datasource_filename)
        )
        cls.domain = cls.static_datasource.domains[0]
        cls.datasource = StaticDataSourceConfiguration._get_datasource_config(
            cls.static_datasource,
            cls.domain,
        )
        cls.casefactory = CaseFactory(domain=cls.domain)

    @classmethod
    def tearDownClass(cls):
        super(BaseICDSDatasourceTest, cls).tearDownClass()
        cls._call_center_domain_mock.stop()

    def tearDown(self):
        FormProcessorTestUtils.delete_all_cases()

    def _rebuild_table_get_query_object(self):
        rebuild_indicators(self.datasource._id)
        adapter = IndicatorSqlAdapter(self.datasource)
        return adapter.get_query_object()

    def _safe_text(input_value):
        if input_value is None:
            return ""
        try:
            return str(input_value)
        except:
            return ""

class TestCCSRecordDataSource(BaseICDSDatasourceTest):
    datasource_filename = 'ccs_record_cases_monthly_tableau'

    def _create_ccs_case(self, case_id, dob, edd, add=None,
            caste="st", minority="no", resident="yes", disabled="no",
            sex="F", last_preg_tt="no", tt_complete_date=None,
            num_anc_complete=0, bp1_date=None, bp2_date=None,
            bp3_date=None, pnc1_date=None, date_death=None,
            date_opened=datetime.utcnow(), date_modified=datetime.utcnow(),
            date_closed=None):
        
        if date_closed is not None:
            closed = True
        else:
            closed = False

        household_case = CaseStructure(
            case_id = "household-" + case_id,
            attrs={
                "case_type":"household",
                "create": True,
                "date_opened": date_opened,
                "date_modified": date_modified,
                "update": dict(
                    hh_caste=caste,
                    hh_minority=minority
                )
            },
        )

        person_case = CaseStructure(
            case_id = "person-" + case_id,
            attrs={
                "case_type":"person",
                "create": True,
                "close": closed,
                "date_opened": date_opened,
                "date_modified": date_modified,
                "update": dict(
                    resident=resident,
                    sex=sex,
                    disabled=disabled,
                    dob=dob,
                    date_death=date_death,
                    last_preg_tt=last_preg_tt,
                )
            },
            indices=[CaseIndex(
                household_case,
                identifier='parent',
                relationship=CASE_INDEX_CHILD,
                related_type=household_case.attrs['case_type'],
            )],
        )

        ccs_record_case = CaseStructure(
            case_id = case_id,
            attrs={
                "case_type":"ccs_record",
                "create": True,
                "close": closed,
                "date_opened": date_opened,
                "date_modified": date_modified,
                "date_closed": date_closed,
                "update": dict(
                    edd=edd,
                    add=add,
                    tt_complete_date=tt_complete_date,
                    num_anc_complete=num_anc_complete,
                    bp1_date=bp1_date,
                    bp2_date=bp2_date,
                    bp3_date=bp3_date,
                    pnc1_date=bp3_date,
                )
            },
            indices=[CaseIndex(
                person_case,
                identifier='parent',
                relationship=CASE_INDEX_CHILD,
                related_type=person_case.attrs['case_type'],
            )],
        )
        self.casefactory.create_or_update_cases([ccs_record_case])
  
  
    def _submit_bp_form(self, form_date, case_id, 
        using_ifa="yes", num_ifa_consumed_last_seven_days=0, anemia=None, 
        extra_meal="no", resting_during_pregnancy="no", counsel_immediate_bf="no",
        counsel_bp_vid="no", counsel_preparation="no", counsel_fp_vid="no",
        counsel_immediate_conception="no", counsel_accessible_postpartum_fp="no"):

        form = ElementTree.Element("data")
        form.attrib['xmlns'] = XMNLS_BP_FORM
        form.attrib['xmlns:jrm'] = "http://openrosa.org/jr/xforms"
        
        meta = ElementTree.Element("meta")
        meta.append(ElementTree.Element("timeEnd", text=form_date.isoformat()))
        form.append(meta)        

        case = ElementTree.Element("case")
        case.attrib["date_modified"] = form_date.isoformat()
        case.attrib["case_id"] = case_id
        case.attrib["xmlns"] = "http://commcarehq.org/case/transaction/v2" 
        form.append(case)
        form.append(ElementTree.Element("play_family_planning_vid", text=_safe_text(counsel_fp_vid)))
        form.append(ElementTree.Element("conceive", text=_safe_text(counsel_immediate_conception)))
    
        bp1 = ElementTree.Element("bp1")
        bp1.append(ElementTree.Element("using_ifa", text=_safe_text(using_ifa)))
        if using_ifa=="yes":
            bp1.append(ElementTree.Element("ifa_last_seven_days", text=_safe_text(num_ifa_consumed_last_seven_days)))
        bp1.append(ElementTree.Element("anemia", text=_safe_text(anemia)))
        bp1.append(ElementTree.Element("eating_extra", text=_safe_text(extra_meal)))
        bp1.append(ElementTree.Element("resting", text=_safe_text(resting_during_pregnancy)))
        form.append(bp1)
        
        bp2 = ElementTree.Element("bp2")
        bp2.append(ElementTree.Element("immediate_breastfeeding", text=_safe_text(counsel_immediate_bf)))
        bp2.append(ElementTree.Element("play_birth_preparedness_vid", text=_safe_text(counsel_bp_vid)))
        bp2.append(ElementTree.Element("counsel_preparation", text=_safe_text(counsel_preparation)))
        form.append(bp2)

        fp_group = ElementTree.Element("family_planning_group")
        fp_group.append(ElementTree.Element("counsel_accessible_ppfp", text=_safe_text(counsel_accessible_postpartum_fp)))
        form.append(fp_group)
        submit_form_locally(form, self.domain, **{})


    def _submit_thr_rations_form(self, form_date, case_id, 
        thr_given_mother="0", rations_distributed=0):

        form = ElementTree.Element("data")
        form.attrib['xmlns'] = XMNLS_THR_FORM
        form.attrib['xmlns:jrm'] = "http://openrosa.org/jr/xforms"
        
        meta = ElementTree.Element("meta")
        meta.append(ElementTree.Element("timeEnd", text=form_date.isoformat()))
        form.append(meta)        

        case = ElementTree.Element("case")
        case.attrib["date_modified"] = form_date.isoformat()
        case.attrib["case_id"] = case_id
        case.attrib["xmlns"] = "http://commcarehq.org/case/transaction/v2" 
        form.append(case)

        form.append(ElementTree.Element("thr_given_mother", text=_safe_text(thr_given_mother)))
        
        if thr_given_mother=="1":
            mother_thr = ElementTree.Element("mother_thr")
            mother_thr.append(ElementTree.Element("days_ration_given_mother", text=_safe_text(rations_distributed)))
            form.append(mother_thr)

        submit_form_locally(form, self.domain, **{})


    def test_open_in_month(self):
        #Opened January 2016
        #Closed March 2016
        #Last Update March 2016
        case_id = "case"
        self._create_ccs_case(
            case_id = case_id,
            dob = datetime.date(1990, 01, 01),
            edd = datetime.date(2016, 06, 02),
            date_opened = datetime.datetime(2016, 01, 10),
            date_modified = datetime.datetime(2016, 03, 12),
            date_closed = datetime.datetime(2016, 03, 12),
        )

        query = self._rebuild_table_get_query_object()
        self.assertEqual(query.count(), 7)

        row = query.all()[0]        
        self.assertEqual(row.month, datetime.date(2015,12,01))
        self.assertEqual(row.open_in_month, 0)
        
        row = query.all()[1]        
        self.assertEqual(row.month, datetime.date(2016,01,01))
        self.assertEqual(row.open_in_month, 1)

        row = query.all()[2]        
        self.assertEqual(row.month, datetime.date(2016,02,01))
        self.assertEqual(row.open_in_month, 1)
        
        row = query.all()[3]
        self.assertEqual(row.month, datetime.date(2016,03,01))
        self.assertEqual(row.open_in_month, 1)
        
        row = query.all()[4]
        self.assertEqual(row.month, datetime.date(2016,04,01))
        self.assertEqual(row.open_in_month, 0)

    #def test_alive_in_month(self):
    #    #Died January 2016
    #    #Remained Open (children alive)

    #    self._create_ccs_case(
    #        case_id = "case",
    #        dob = datetime.date(1990, 01, 01),
    #        edd = datetime.date(2016, 06, 02),
    #        date_opened = datetime.datetime(2016, 01, 10),
    #        date_modified = datetime.datetime(2016, 03, 12),
    #        date_death = datetime.date(2016,01,10),
    #    )

    #    query = self._rebuild_table_get_query_object()
    #    self.assertEqual(query.count(), 7)

    #    row = query.all()[0]        
    #    self.assertEqual(row.month, datetime.date(2015,12,01))
    #    self.assertEqual(row.alive_in_month, 1)
        
    #    row = query.all()[1]        
    #    self.assertEqual(row.month, datetime.date(2016,01,01))
    #    self.assertEqual(row.alive_in_month, 1)

    #    row = query.all()[2]        
    #    self.assertEqual(row.month, datetime.date(2016,02,01))
    #    self.assertEqual(row.alive_in_month, 0)
        
    #    row = query.all()[3]
    #    self.assertEqual(row.month, datetime.date(2016,03,01))
    #    self.assertEqual(row.alive_in_month, 0)

    #def test_lactating_post(self):
    #    #Add was mid august 2015
    #    #Lactating ends mid february 2016
        
    #    self._create_ccs_case(
    #        case_id = "case",
    #        dob = datetime.date(1990, 01, 01),
    #        add = datetime.date(2015, 08, 15),
    #        edd = datetime.date(2015, 08, 10),
    #        date_opened = datetime.datetime(2015, 02, 10),
    #        date_modified = datetime.datetime(2016, 03, 12),
    #    )

    #    query = self._rebuild_table_get_query_object()
    #    self.assertEqual(query.count(), 7)
        
    #    row = query.all()[1]        
    #    self.assertEqual(row.month, datetime.date(2016,01,01))
    #    self.assertEqual(row.lactating, 1)
    #    self.assertEqual(row.ccs_status, "lactating")

    #    row = query.all()[2]        
    #    self.assertEqual(row.month, datetime.date(2016,02,01))
    #    self.assertEqual(row.lactating, 1)
    #    self.assertEqual(row.ccs_status, "lactating")
        
    #    row = query.all()[3]
    #    self.assertEqual(row.month, datetime.date(2016,03,01))
    #    self.assertEqual(row.lactating, 0)
    #    self.assertEqual(row.ccs_status, "other")

    #    row = query.all()[4]
    #    self.assertEqual(row.month, datetime.date(2016,04,01))
    #    self.assertEqual(row.lactating, 0)
    #    self.assertEqual(row.ccs_status, "other")

    #def test_preg_to_lactating(self):
    #    #Add was february 2015
        
    #    self._create_ccs_case(
    #        case_id = "case",
    #        dob = datetime.date(1990, 01, 01),
    #        add = datetime.date(2016, 02, 15),
    #        edd = datetime.date(2016, 02, 10),
    #        date_opened = datetime.datetime(2015, 02, 10),
    #        date_modified = datetime.datetime(2016, 03, 12),
    #    )

    #    query = self._rebuild_table_get_query_object()
    #    self.assertEqual(query.count(), 7)
        
    #    row = query.all()[1]        
    #    self.assertEqual(row.month, datetime.date(2016,01,01))
    #    self.assertEqual(row.pregnant, 1)
    #    self.assertEqual(row.lactating, 0)
    #    self.assertEqual(row.ccs_status, "pregnant")

    #    row = query.all()[2]        
    #    self.assertEqual(row.month, datetime.date(2016,02,01))
    #    self.assertEqual(row.pregnant, 1)
    #    self.assertEqual(row.lactating, 0)
    #    self.assertEqual(row.ccs_status, "pregnant")
        
    #    row = query.all()[3]
    #    self.assertEqual(row.month, datetime.date(2016,03,01))
    #    self.assertEqual(row.pregnant, 0)
    #    self.assertEqual(row.lactating, 1)
    #    self.assertEqual(row.ccs_status, "lactating")

    #    row = query.all()[4]
    #    self.assertEqual(row.month, datetime.date(2016,04,01))
    #    self.assertEqual(row.pregnant, 0)
    #    self.assertEqual(row.lactating, 1)
    #    self.assertEqual(row.ccs_status, "lactating")

    #def test_pre_preg(self):
    #    #opened and updated in march
    #    #edd is nov 2016 (lmp in february)
        
    #    self._create_ccs_case(
    #        case_id = "case",
    #        dob = datetime.date(1990, 01, 01),
    #        edd = datetime.date(2016, 11, 10),
    #        date_opened = datetime.datetime(2015, 03, 10),
    #        date_modified = datetime.datetime(2016, 03, 12),
    #    )

    #    query = self._rebuild_table_get_query_object()
    #    self.assertEqual(query.count(), 7)
        
    #    row = query.all()[1] 
    #    self.assertEqual(row.month, datetime.date(2016,01,01))
    #    self.assertEqual(row.pregnant, 0)
    #    self.assertEqual(row.ccs_status, "other")

    #    row = query.all()[2]
    #    self.assertEqual(row.month, datetime.date(2016,02,01))
    #    self.assertEqual(row.pregnant, 1)
    #    self.assertEqual(row.ccs_status, "pregnant")
        
    #    row = query.all()[3]
    #    self.assertEqual(row.month, datetime.date(2016,03,01))
    #    self.assertEqual(row.pregnant, 1)
    #    self.assertEqual(row.ccs_status, "pregnant")

    #    row = query.all()[4]
    #    self.assertEqual(row.month, datetime.date(2016,04,01))
    #    self.assertEqual(row.pregnant, 1)
    #    self.assertEqual(row.ccs_status, "pregnant")

    #def test_demographic_data(self):
    #    self._create_ccs_case(
    #        case_id = "case",
    #        caste = "sc",
    #        minority = "yes",
    #        resident = "yes",
    #        disabled="yes",
    #        dob = datetime.date(1990, 01, 01),
    #        edd = datetime.date(2016, 11, 10),
    #        date_opened = datetime.datetime(2015, 03, 10),
    #        date_modified = datetime.datetime(2016, 03, 12),
    #    )

    #    query = self._rebuild_table_get_query_object()
    #    self.assertEqual(query.count(), 7)
        
    #    row = query.all()[0]
    #    self.assertEqual(row.caste, "sc")
    #    self.assertEqual(row.disabled, "yes")
    #    self.assertEqual(row.minority, "yes")
    #    self.assertEqual(row.resident, "yes")

    #def test_trimester_1_2(self):
    #    #edd is september
        
    #    self._create_ccs_case(
    #        case_id = "case",
    #        dob = datetime.date(1990, 01, 01),
    #        edd = datetime.date(2016, 09, 10),
    #        date_opened = datetime.datetime(2015, 12, 10),
    #        date_modified = datetime.datetime(2016, 03, 12),
    #    )

    #    query = self._rebuild_table_get_query_object()
    #    self.assertEqual(query.count(), 7)
        
    #    row = query.all()[1] 
    #    self.assertEqual(row.month, datetime.date(2016,01,01))
    #    self.assertEqual(row.trimester, 1)

    #    row = query.all()[2]
    #    self.assertEqual(row.month, datetime.date(2016,02,01))
    #    self.assertEqual(row.trimester, 1)
        
    #    row = query.all()[3]
    #    self.assertEqual(row.month, datetime.date(2016,03,01))
    #    self.assertEqual(row.trimester, 2)

    #    row = query.all()[4]
    #    self.assertEqual(row.month, datetime.date(2016,04,01))
    #    self.assertEqual(row.trimester, 2)

    #def test_trimester_3_none(self):
    #    #edd and add is march
        
    #    self._create_ccs_case(
    #        case_id = "case",
    #        dob = datetime.date(1990, 01, 01),
    #        edd = datetime.date(2016, 03, 10),
    #        add = datetime.date(2016, 03, 12),
    #        date_opened = datetime.datetime(2015, 12, 10),
    #        date_modified = datetime.datetime(2016, 03, 12),
    #    )

    #    query = self._rebuild_table_get_query_object()
    #    self.assertEqual(query.count(), 7)
        
    #    row = query.all()[1] 
    #    self.assertEqual(row.month, datetime.date(2016,01,01))
    #    self.assertEqual(row.trimester, 3)

    #    row = query.all()[2]
    #    self.assertEqual(row.month, datetime.date(2016,02,01))
    #    self.assertEqual(row.trimester, 3)
        
    #    row = query.all()[3]
    #    self.assertEqual(row.month, datetime.date(2016,03,01))
    #    self.assertEqual(row.trimester, 3)

    #    row = query.all()[4]
    #    self.assertEqual(row.month, datetime.date(2016,04,01))
    #    self.assertEqual(row.trimester, None)

    #def test_thr_rations(self):
    #    #edd is september
        
    #    self._create_ccs_case(
    #        case_id = "case",
    #        dob = datetime.date(1990, 01, 01),
    #        edd = datetime.date(2016, 09, 10),
    #        date_opened = datetime.datetime(2015, 12, 10),
    #        date_modified = datetime.datetime(2016, 03, 12),
    #    )

    #    self._submit_thr_rations_form(
    #        form_date=datetime.date(2015,02,02), 
    #        case_id="case", 
    #        thr_given_mother="1",
    #        rations_distributed=5,
    #    )

    #    self._submit_thr_rations_form(
    #        form_date=datetime.date(2015,02,06), 
    #        case_id="case", 
    #        thr_given_mother="1",
    #        rations_distributed=6,
    #    )

    #    self._submit_thr_rations_form(
    #        form_date=datetime.date(2015,03,10), 
    #        case_id="case", 
    #        thr_given_mother="1",
    #        rations_distributed=21,
    #    )

    #    query = self._rebuild_table_get_query_object()
    #    self.assertEqual(query.count(), 7)
        
    #    row = query.all()[1]
    #    self.assertEqual(row.month, datetime.date(2016,01,01))
    #    self.assertEqual(row.num_rations_distributed, None)
    #    self.assertEqual(row.rations_21_plus_distributed, 0)


    #    row = query.all()[2]
    #    self.assertEqual(row.month, datetime.date(2016,02,01))
    #    self.assertEqual(row.num_rations_distributed, 11)
    #    self.assertEqual(row.rations_21_plus_distributed, 0)
        
    #    row = query.all()[3]
    #    self.assertEqual(row.month, datetime.date(2016,03,01))
    #    self.assertEqual(row.num_rations_distributed, 21)
    #    self.assertEqual(row.rations_21_plus_distributed, 1)

    #    row = query.all()[4]
    #    self.assertEqual(row.month, datetime.date(2016,04,01))
    #    self.assertEqual(row.num_rations_distributed, None)
    #    self.assertEqual(row.rations_21_plus_distributed, 0)
        
        
