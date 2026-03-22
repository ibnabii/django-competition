from enum import Enum

from .capabilities import Capability


class Role(Enum):
    # PARTICIPANT = "participant"  # TODO: do i want it?
    JUDGE = "judge"
    JUDGE_FINALS = "judge_finals"
    JUDGE_BOS = "judge_bos"
    HEAD_JUDGE = "head_judge"
    MANAGER = "manager"
    ENTRY_MANAGER = "entry_manager"
    ENTRY_CODER = "entry_coder"
    TRANSLATOR = "translators"


GLOBAL_ROLE_CAPABILITIES = {
    Role.TRANSLATOR: {
        Capability.SYSTEM_TRANSLATE,
    },
}

GLOBAL_ROLE_NAMES = [role.value for role in GLOBAL_ROLE_CAPABILITIES.keys()]

LIST_ROLES_JUDGES = [Role.JUDGE, Role.JUDGE_FINALS, Role.JUDGE_BOS]

CONTEST_ROLE_CAPABILITIES = {
    Role.JUDGE: {
        Capability.VIEW_JUDGING_ENTRIES_LIST,
        Capability.EDIT_SCORESHEET,
        Capability.VIEW_SCORESHEET,
    },
    Role.JUDGE_FINALS: {
        Capability.JUDGE_FINALS,
        Capability.VIEW_SCORESHEET,
    },
    Role.JUDGE_BOS: {Capability.JUDGE_BOS},
    Role.HEAD_JUDGE: {
        Capability.VIEW_JUDGING_ENTRIES_LIST,
        Capability.JUDGE_FINALS,
        Capability.JUDGE_BOS,
        Capability.CONTEST_MANAGE_JUDGES,
    },
    Role.MANAGER: {Capability.CONTEST_MANAGE_TEAM, Capability.CONTEST_MANAGE_JUDGES},
    Role.ENTRY_MANAGER: {Capability.ENTRY_RECEIVE, Capability.ENTRY_PAYMENTS},
    Role.ENTRY_CODER: {Capability.ENTRY_ENCODE, Capability.ENTRY_DECODE},
}
