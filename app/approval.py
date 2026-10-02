from .db import fetch_all, fetch_one, get_db

CONTENT_TABLES = {
    "articles": ("articles", "slug"),
    "courses": ("courses", "slug"),
    "news": ("news", "slug"),
}

# These are the only content-manager users allowed to approve their own work.
# Keep this allowlist username-based so it remains stable if database IDs differ
# between development and production.
OWNER_APPROVER_USERNAMES = frozenset({"charles.yung", "francis.lau"})


def can_approve_own_content(user_id):
    user = fetch_one(
        "SELECT username FROM admin_users WHERE id=%s AND is_active=1",
        (user_id,),
    )
    return bool(user and user["username"] in OWNER_APPROVER_USERNAMES)


def available_reviewers(submitter_id):
    return fetch_all(
        """SELECT id,username FROM admin_users
        WHERE is_active=1 AND username<>'admin'
          AND (id<>%s OR username IN (%s,%s))
        ORDER BY username""",
        (submitter_id, *sorted(OWNER_APPROVER_USERNAMES)),
    )


def default_reviewer_ids(submitter_id, reviewer_options=None):
    options = reviewer_options if reviewer_options is not None else available_reviewers(submitter_id)
    # The query only includes the submitter for the two allowlisted owner
    # approvers, so this check avoids a second database lookup when rendering
    # reviewer controls.
    if any(option["id"] == submitter_id for option in options):
        return [submitter_id]
    return [options[0]["id"]] if len(options) == 1 else []


def reviewer_options(submitter_id, content_type=None, content_key=None, selected_override=None, locale="zh-Hant"):
    options = available_reviewers(submitter_id)
    if selected_override is not None:
        selected_ids = {int(value) for value in selected_override if str(value).isdigit()}
    elif content_type and content_key:
        rows = fetch_all(
            """SELECT r.reviewer_id FROM content_approval_reviewers r
            JOIN content_approvals a ON a.id=r.approval_id
            WHERE a.content_type=%s AND a.content_key=%s AND a.locale=%s""",
            (content_type, content_key, locale),
        )
        selected_ids = {row["reviewer_id"] for row in rows}
    else:
        selected_ids = set()
    if not selected_ids and selected_override is None:
        selected_ids.update(default_reviewer_ids(submitter_id, options))
    for option in options:
        option["selected"] = option["id"] in selected_ids
    return options


def validate_reviewers(submitter_id, reviewer_ids):
    requested = {int(value) for value in reviewer_ids if str(value).isdigit()}
    available = {reviewer["id"] for reviewer in available_reviewers(submitter_id)}
    selected = sorted(requested & available)
    if not selected:
        if can_approve_own_content(submitter_id):
            raise ValueError("Select at least one active reviewer, including yourself or another reviewer.")
        raise ValueError("Select at least one active reviewer other than the content creator.")
    if requested != set(selected):
        raise ValueError("One or more selected reviewers are invalid or inactive.")
    return selected


def submit_for_review(content_type, content_key, submitter_id, reviewer_ids, locale="zh-Hant"):
    if content_type not in CONTENT_TABLES:
        raise ValueError("Invalid content type")
    selected = validate_reviewers(submitter_id, reviewer_ids)
    with get_db().cursor() as cursor:
        cursor.execute(
            """INSERT INTO content_approvals (content_type,content_key,locale,submitted_by,status,submitted_at,approved_at)
            VALUES (%s,%s,%s,%s,'pending',NOW(),NULL)
            ON DUPLICATE KEY UPDATE submitted_by=VALUES(submitted_by),status='pending',submitted_at=NOW(),approved_at=NULL""",
            (content_type, content_key, locale, submitter_id),
        )
        cursor.execute("SELECT id FROM content_approvals WHERE content_type=%s AND content_key=%s AND locale=%s", (content_type, content_key, locale))
        approval_id = cursor.fetchone()["id"]
        cursor.execute("DELETE FROM content_approval_votes WHERE approval_id=%s", (approval_id,))
        cursor.execute("DELETE FROM content_approval_reviewers WHERE approval_id=%s", (approval_id,))
        cursor.executemany(
            "INSERT INTO content_approval_reviewers (approval_id,reviewer_id) VALUES (%s,%s)",
            [(approval_id, reviewer_id) for reviewer_id in selected],
        )


def approval_state(content_type, content_key, current_user_id, locale="zh-Hant"):
    approval = fetch_one(
        """SELECT a.id,a.submitted_by,a.status,u.username submitted_by_name
        FROM content_approvals a JOIN admin_users u ON u.id=a.submitted_by
        WHERE a.content_type=%s AND a.content_key=%s AND a.locale=%s""", (content_type, content_key, locale)
    )
    if not approval:
        return None
    required = fetch_all(
        "SELECT reviewer_id FROM content_approval_reviewers WHERE approval_id=%s",
        (approval["id"],),
    )
    votes = fetch_all("SELECT reviewer_id FROM content_approval_votes WHERE approval_id=%s", (approval["id"],))
    required_ids = {row["reviewer_id"] for row in required}
    voted_ids = {row["reviewer_id"] for row in votes}
    approval["required"] = len(required_ids)
    approval["approved"] = len(required_ids & voted_ids)
    approval["can_approve"] = (
        approval["status"] == "pending"
        and current_user_id in required_ids
        and current_user_id not in voted_ids
    )
    return approval


def attach_approval_states(content_type, items, current_user_id, locale=None):
    for item in items:
        active_locale = locale or item.get("original_locale", "zh-Hant")
        item["approval"] = approval_state(content_type, item["slug"], current_user_id, active_locale)
    return items


def approve(content_type, content_key, reviewer_id, locale="zh-Hant"):
    if content_type not in CONTENT_TABLES:
        raise ValueError("Invalid content type")
    state = approval_state(content_type, content_key, reviewer_id, locale)
    if not state or not state["can_approve"]:
        raise ValueError("You are not assigned to approve this content.")
    with get_db().cursor() as cursor:
        cursor.execute(
            "INSERT IGNORE INTO content_approval_votes (approval_id,reviewer_id) VALUES (%s,%s)",
            (state["id"], reviewer_id),
        )
    state = approval_state(content_type, content_key, reviewer_id, locale)
    if state["required"] > 0 and state["approved"] == state["required"]:
        with get_db().cursor() as cursor:
            cursor.execute("UPDATE content_approvals SET status='approved',approved_at=NOW() WHERE id=%s", (state["id"],))
            original = fetch_one(f"SELECT original_locale FROM `{CONTENT_TABLES[content_type][0]}` WHERE slug=%s", (content_key,))
            if original and locale == original["original_locale"]:
                table, key_column = CONTENT_TABLES[content_type]
                if content_type == "courses":
                    cursor.execute(f"UPDATE `{table}` SET status='posted',is_published=1,posted_at=COALESCE(posted_at,NOW()) WHERE `{key_column}`=%s", (content_key,))
                else:
                    cursor.execute(f"UPDATE `{table}` SET status='posted',posted_at=COALESCE(posted_at,NOW()) WHERE `{key_column}`=%s", (content_key,))
            else:
                cursor.execute("UPDATE content_translations SET status='posted',posted_at=COALESCE(posted_at,NOW()) WHERE content_type=%s AND content_key=%s AND locale=%s", (content_type, content_key, locale))
        return True
    return False
