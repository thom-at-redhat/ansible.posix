# (c) 2017, Tennis Smith, https://github.com/gamename
# (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
    name: profile_roles
    type: aggregate
    short_description: adds timing information to roles
    description:
        - This callback module provides profiling for ansible roles.
    requirements:
      - whitelisting in configuration
    options:
      summary_only:
        description:
          - Only show summary, not individual task profiles.
            Especially usefull in combination with C(DISPLAY_SKIPPED_HOSTS=false) and/or C(ANSIBLE_DISPLAY_OK_HOSTS=false).
        type: bool
        default: False
        env:
          - name: PROFILE_ROLES_SUMMARY_ONLY
        ini:
          - section: callback_profile_roles
            key: summary_only
        version_added: 1.5.0
'''

import collections
import time

from ansible.plugins.callback import CallbackBase
from ansible.module_utils.six.moves import reduce

# define start time
t0 = tn = time.time()


def secondsToStr(t):
    # http://bytes.com/topic/python/answers/635958-handy-short-cut-formatting-elapsed-time-floating-point-seconds
    def rediv(ll, b):
        return list(divmod(ll[0], b)) + ll[1:]

    return "%d:%02d:%02d.%03d" % tuple(
        reduce(rediv, [[t * 1000, ], 1000, 60, 60]))


def filled(msg, fchar="*"):
    if len(msg) == 0:
        width = 79
    else:
        msg = "%s " % msg
        width = 79 - len(msg)
    if width < 3:
        width = 3
    filler = fchar * width
    return "%s%s " % (msg, filler)


def timestamp(self):
    if self.current is not None:
        self.stats[self.current] = time.time() - self.stats[self.current]
        self.totals[self.current] += self.stats[self.current]


def tasktime():
    global tn
    time_current = time.strftime('%A %d %B %Y  %H:%M:%S %z')
    time_elapsed = secondsToStr(time.time() - tn)
    time_total_elapsed = secondsToStr(time.time() - t0)
    tn = time.time()
    return filled('%s (%s)%s%s' %
                  (time_current, time_elapsed, ' ' * 7, time_total_elapsed))


class CallbackModule(CallbackBase):
    """
    This callback module provides profiling for ansible roles.
    """
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'aggregate'
    CALLBACK_NAME = 'ansible.posix.profile_roles'
    CALLBACK_NEEDS_WHITELIST = True

    def __init__(self):
        self.stats = collections.Counter()
        self.totals = collections.Counter()
        self.current = None

        self.summary_only = None

        super(CallbackModule, self).__init__()

    def set_options(self, task_keys=None, var_options=None, direct=None):

        super(CallbackModule, self).set_options(task_keys=task_keys, var_options=var_options, direct=direct)

        self.summary_only = self.get_option('summary_only')

    def _display_tasktime(self):
        if not self.summary_only:
            self._display.display(tasktime())

    def _record_task(self, task):
        """
        Logs the start of each task
        """
        self._display_tasktime()
        timestamp(self)

        if task._role:
            self.current = task._role._role_name
        else:
            self.current = task.action

        self.stats[self.current] = time.time()

    def v2_playbook_on_task_start(self, task, is_conditional):
        self._record_task(task)

    def v2_playbook_on_handler_task_start(self, task):
        self._record_task(task)

    def v2_playbook_on_stats(self, stats):
        # Align summary report header with other callback plugin summary
        self._display.banner("ROLES RECAP")

        self._display.display(tasktime())
        self._display.display(filled("", fchar="="))

        timestamp(self)
        total_time = sum(self.totals.values())

        # Print the timings starting with the largest one
        for result in self.totals.most_common():
            msg = u"{0:-<70}{1:->9}".format(result[0] + u' ', u' {0:.02f}s'.format(result[1]))
            self._display.display(msg)

        msg_total = u"{0:-<70}{1:->9}".format(u'total ', u' {0:.02f}s'.format(total_time))
        self._display.display(filled("", fchar="~"))
        self._display.display(msg_total)
