from employees.models import Employee
from organization.models import Branch, Division

ACTIONS = {
    "employee.created": "Pegawai ditambahkan",
    "employee.updated": "Data pegawai diubah",
    "branch.created": "Cabang ditambahkan",
    "branch.updated": "Cabang diubah",
    "division.created": "Divisi ditambahkan",
    "division.updated": "Divisi diubah",
    "division.deleted": "Divisi dihapus",
    "division.settings_changed": "Pengaturan divisi diubah",
}
TARGETS = {
    "employee": (Employee, "full_name"),
    "branch": (Branch, "name"),
    "division": (Division, "name"),
}


def safe_changes(event):
    if event.action != "division.settings_changed" or not isinstance(event.changes, dict):
        return {}
    changes = {}
    for key in ("kinerja_enabled", "pelimpahan_enabled"):
        item = event.changes.get(key)
        if (
            isinstance(item, dict)
            and type(item.get("old")) is bool
            and type(item.get("new")) is bool
        ):
            changes[key] = {"old": item["old"], "new": item["new"]}
    return changes


def present_events(events):
    labels = {}
    for kind, (model, field) in TARGETS.items():
        ids = {
            event.target_id
            for event in events
            if event.action in ACTIONS and event.action.split(".")[0] == kind
        }
        if ids:
            labels[kind] = dict(model.objects.filter(pk__in=ids).values_list("pk", field))
    result = []
    for event in events:
        kind = event.action.split(".")[0] if event.action in ACTIONS else "unknown"
        result.append(
            {
                "id": event.pk,
                "created_at": event.created_at.isoformat(),
                "actor": {"id": event.actor_id, "email": event.actor.email},
                "action": event.action,
                "action_label": ACTIONS.get(event.action, "Aktivitas lain"),
                "target": {
                    "type": kind,
                    "id": str(event.target_id),
                    "label": labels.get(kind, {}).get(event.target_id),
                },
                "changes": safe_changes(event),
            }
        )
    return result
