import datetime
from decimal import Decimal

from django.conf import settings
from django.core.urlresolvers import reverse

from timepiece import models as timepiece
from timepiece import forms as timepiece_forms
from timepiece.tests.base import TimepieceDataTestCase

from dateutil import relativedelta


class PayrollTest(TimepieceDataTestCase):
    def log_time(self, delta=None, billable=True, project=None, start=None, status=None):
        if delta:
            hours, minutes = delta
        else:
            hours = 4
            minutes = 0
        if not start:
            start = datetime.datetime.now()
        end = start + datetime.timedelta(hours=hours, minutes=minutes)
        data = {'user': self.user,
                'start_time': start,
                'end_time': end,
                }
        if billable:
            data['activity'] = self.devl_activity
        if project:
            data['project'] = project
        else:
            data['project'] = self.create_project(billable=billable)
        if status:
            data['status'] = status
        return self.create_entry(data)

    def testPersonSummary(self):
        sick = self.create_project()
        vacation = self.create_project()
        settings.TIMEPIECE_PROJECTS = {'sick': sick.pk, 'vacation': vacation.pk}
        rp = self.create_person_repeat_period({'user': self.user})
        start = datetime.date.today().replace(day=1)
        end = start + relativedelta.relativedelta(months=1)
        billable = self.log_time(delta=(3, 30), status='approved')
        non_billable = self.log_time(delta=(2, 0), billable=False, status='approved')
        #summary['total'] does not increase from unverified hours
        unapproved = self.log_time(delta=(5, 0), status='verified')
        sick = self.log_time(delta=(8, 0), project=sick, status='approved')
        vacation = self.log_time(delta=(4, 0), project=vacation, status='approved')
        summary = rp.summary(start, end)
        self.assertEqual(summary['billable'], Decimal('3.50'))
        self.assertEqual(summary['non_billable'], Decimal('2.00'))
        self.assertEqual(summary['paid_leave']['sick'], Decimal('8.00'))
        self.assertEqual(summary['paid_leave']['vacation'], Decimal('4.00'))
        self.assertEqual(summary['total'], Decimal('17.50'))

    def testWeeklyHours(self):
        """ Test basic functionality of hours worked per week """
        rp = self.create_person_repeat_period({'user': self.user})
        p1 = self.create_project()
        start = datetime.datetime(2011, 1, 3)
        self.log_time(project=p1, start=start, delta=(8, 0), status='approved')        
        start = datetime.datetime(2011, 1, 4)
        self.log_time(project=p1, start=start, delta=(8, 0), status='approved')
        #rp.hours_in_week total does not add the five unapproved hours
        start = datetime.datetime(2011, 1, 5)
        self.log_time(project=p1, start=start, delta=(5, 0), status='verified')
        self.assertEqual(rp.hours_in_week(start), Decimal('16.00'))

    def testWeeklyHoursBounds(self):
        """ Make sure hours worked on Sunday's don't overlap weekly hours """
        rp = self.create_person_repeat_period({'user': self.user})
        p1 = self.create_project()
        start1 = datetime.datetime(2011, 1, 2)
        self.log_time(project=p1, start=start1, delta=(8, 0), status='approved')
        start2 = datetime.datetime(2011, 1, 9)
        self.log_time(project=p1, start=start2, delta=(8, 0), status='approved')
        self.assertEqual(rp.hours_in_week(start1), Decimal('8.00'))
        self.assertEqual(rp.hours_in_week(start2), Decimal('8.00'))

    def testWeeklyOvertimeHours(self):
        """ Test weekly overtime calculation """
        rp = self.create_person_repeat_period({'user': self.user})
        p1 = self.create_project()
        start1 = datetime.datetime(2011, 1, 2)
        self.log_time(project=p1, start=start1, delta=(44, 0), status='approved')
        self.assertEqual(rp.overtime_hours_in_week(start1), Decimal('4.00'))

    def testWeeklyNonOvertimeHours(self):
        """ Test weekly overtime calculation """
        rp = self.create_person_repeat_period({'user': self.user})
        p1 = self.create_project()
        start1 = datetime.datetime(2011, 1, 2)
        self.log_time(project=p1, start=start1, delta=(40, 0), status='approved')
        self.assertEqual(rp.overtime_hours_in_week(start1), Decimal('0.00'))

    def testMonthlyOvertimeHours(self):
        """ Test monthly overtime calculation """
        rp = self.create_person_repeat_period({'user': self.user})
        p1 = self.create_project()
        start1 = datetime.datetime(2011, 1, 2)
        self.log_time(project=p1, start=start1, delta=(44, 0), status='approved')
        start1 = datetime.datetime(2011, 1, 9)
        self.log_time(project=p1, start=start1, delta=(44, 0), status='approved')
        self.assertEqual(rp.total_monthly_overtime(start1), Decimal('8.00'))           

