from enum import Enum


class Capability(Enum):
    # JUDGE = "judge"
    JUDGE_FINALS = "judge_finals"
    JUDGE_BOS = "judge_bos"
    VIEW_JUDGING_ENTRIES_LIST = "view_judging_entries_list"
    EDIT_SCORESHEET = "edit_scoresheet"
    VIEW_SCORESHEET = "view_scoresheet"

    CONTEST_MANAGE_TEAM = "contest_manage_team"
    CONTEST_MANAGE_JUDGES = "contest_manage_judges"

    ENTRY_RECEIVE = "entry_receive"
    ENTRY_PAYMENTS = "entry_payments"
    ENTRY_ENCODE = "entry_encode"
    ENTRY_DECODE = "entry_decode"

    SYSTEM_TRANSLATE = "system_translate"


CAPABILITIES = {
    Capability.VIEW_JUDGING_ENTRIES_LIST: {
        "description": "Can view list of entries to be judged",
        "scope": "contest",
    },
    Capability.EDIT_SCORESHEET: {
        "description": "Can create or edit scoresheet",
        "scope": "contest",
    },
    Capability.VIEW_SCORESHEET: {
        "description": "Can view (read-only) scoresheet",
        "scope": "contest",
    },
    Capability.JUDGE_FINALS: {
        "description": "Can judge entries in finals, ie. select top 3 entries in each category",
        "scope": "contest",
    },
    Capability.JUDGE_BOS: {
        "description": "Can judge entries in BOS, ie. select best entry in competition out of category winners",
        "scope": "contest",
    },
    Capability.CONTEST_MANAGE_TEAM: {
        "description": "Can manage contest team - add roles within contest",
        "scope": "contest",
    },
    Capability.CONTEST_MANAGE_JUDGES: {
        "description": "Can manage contest judges - add and remove judges from contest",
        "scope": "contest",
    },
    Capability.ENTRY_RECEIVE: {
        "description": "Can mark contest entries as received",
        "scope": "contest",
    },
    Capability.ENTRY_PAYMENTS: {
        "description": "Can mark contest entries as paid",
        "scope": "contest",
    },
    Capability.ENTRY_ENCODE: {
        "description": "Can encode contest entries (ie translate codes as seen by participants to judging codes",
        "scope": "contest",
    },
    Capability.ENTRY_DECODE: {
        "description": "Can decode contest entries (ie translate judging codes to codes seen by participants)",
        "scope": "contest",
    },
    Capability.SYSTEM_TRANSLATE: {
        "description": "Can translate system messages via Rosetta",
        "scope": "global",
    },
}

GLOBAL_CAPABILITIES = {
    cap for cap, meta in CAPABILITIES.items() if meta["scope"] == "global"
}

CONTEST_CAPABILITIES = {
    cap for cap, meta in CAPABILITIES.items() if meta["scope"] == "contest"
}
