# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.cloud import firestore
from google.genai import types

from .a2ui_utils import a2ui_callback

MODEL = "gemini-3.8-flash"
PROJECT_ID = "qwiklabs-gcp-04-9dceb0c15b1a"


def _get_db() -> firestore.Client:
    """Returns a Firestore client initialized with the hardcoded project ID."""
    return firestore.Client(project=PROJECT_ID)


def list_contacts() -> List[Dict[str, Any]]:
    """List all contacts stored in OmniCRM with their basic profiles, preferred channels, and communication styles.

    Returns:
        A list of contact dictionaries containing contact IDs, names, relationships,
        preferred channels, and communication style notes.
    """
    db = _get_db()
    docs = db.collection("contacts").stream()
    contacts = []
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        contacts.append(data)
    return contacts


def get_contact(name_or_id: str) -> Dict[str, Any]:
    """Retrieve complete profile, communication preferences, and style guides for a specific contact.

    Args:
        name_or_id: The document ID or name of the contact to look up.

    Returns:
        A dictionary with the contact's details, or a message indicating the contact was not found.
    """
    db = _get_db()
    contacts_ref = db.collection("contacts")

    # Try exact document ID match first
    doc = contacts_ref.document(name_or_id.lower().replace(" ", "_")).get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = doc.id
        return data

    # Otherwise search by name
    for d in contacts_ref.stream():
        data = d.to_dict()
        if (
            d.id.lower() == name_or_id.lower()
            or name_or_id.lower() in data.get("name", "").lower()
        ):
            data["id"] = d.id
            return data

    return {"error": f"No contact found matching '{name_or_id}'."}


def save_contact(
    name: str,
    relationship: str,
    preferred_channel: str,
    tone_preference: str,
    channels: Optional[List[str]] = None,
    notes: Optional[str] = None,
    communication_style: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Create or update a contact in OmniCRM with their communication profile and style guidelines.

    Args:
        name: Full name of the contact.
        relationship: Relationship description (e.g. 'Colleague', 'Client', 'Friend').
        preferred_channel: Primary communication channel (e.g. 'whatsapp', 'imessage', 'gmail', 'google_chat').
        tone_preference: Tone description (e.g. 'concise, casual, direct').
        channels: List of active chat platforms (e.g. ['whatsapp', 'gmail']).
        notes: Personal context, scheduling preferences, or topics of interest.
        communication_style: Platform-specific guidance (e.g. {'whatsapp': 'short sentences', 'gmail': 'formal'}).

    Returns:
        Status dictionary confirming the contact creation/update.
    """
    db = _get_db()
    contact_id = name.lower().replace(" ", "_")
    doc_ref = db.collection("contacts").document(contact_id)

    payload = {
        "name": name,
        "relationship": relationship,
        "preferred_channel": preferred_channel.lower(),
        "tone_preference": tone_preference,
        "channels": [c.lower() for c in (channels or [preferred_channel])],
        "notes": notes or "",
        "communication_style": communication_style or {},
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    doc_ref.set(payload, merge=True)
    return {"status": "success", "contact_id": contact_id, "contact": payload}


def update_contact_style(
    contact_id: str,
    channel: str,
    style_observation: str,
    notes_update: Optional[str] = None,
) -> Dict[str, Any]:
    """Record learned style patterns or communication notes for a contact on a specific platform.

    Args:
        contact_id: The ID of the contact.
        channel: The platform where the style was observed (e.g. 'whatsapp', 'gmail', 'google_chat', 'imessage').
        style_observation: New style rule or nuance learned (e.g., 'uses bullet points, avoids emojis, signs off with Best').
        notes_update: Additional notes to append to the contact's profile.

    Returns:
        Status dictionary confirming the style update.
    """
    db = _get_db()
    doc_ref = db.collection("contacts").document(contact_id)
    doc = doc_ref.get()
    if not doc.exists:
        return {"error": f"Contact '{contact_id}' not found."}

    data = doc.to_dict()
    current_style = data.get("communication_style", {})
    current_style[channel.lower()] = style_observation

    updates: Dict[str, Any] = {
        "communication_style": current_style,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if notes_update:
        existing_notes = data.get("notes", "")
        updates["notes"] = f"{existing_notes}\n{notes_update}".strip()

    doc_ref.update(updates)
    return {
        "status": "success",
        "contact_id": contact_id,
        "channel": channel,
        "style": style_observation,
    }


def draft_recommended_message(
    contact_name_or_id: str,
    channel: str,
    intent: str,
) -> Dict[str, Any]:
    """Fetch contact profile and formulate a tailored message recommendation based on recorded style rules.

    Args:
        contact_name_or_id: The contact's name or ID.
        channel: The target platform (e.g. 'whatsapp', 'gmail', 'google_chat', 'imessage').
        intent: The message intent, topic, or key points to convey.

    Returns:
        A dictionary containing the contact's style guide for the channel and draft recommendations.
    """
    contact = get_contact(contact_name_or_id)
    if "error" in contact:
        return contact

    style_guide = contact.get("communication_style", {}).get(
        channel.lower(),
        contact.get("tone_preference", "natural and clear"),
    )

    return {
        "contact_name": contact.get("name"),
        "channel": channel,
        "general_tone": contact.get("tone_preference"),
        "channel_style_guide": style_guide,
        "notes": contact.get("notes"),
        "intent_to_convey": intent,
        "instruction": (
            f"Draft a message for {contact.get('name')} on {channel} conveying: '{intent}'. "
            f"Adhere closely to the style guide: '{style_guide}'."
        ),
    }


def log_interaction(
    contact_name_or_id: str,
    channel: str,
    message_text: str,
    direction: str = "received",
) -> Dict[str, Any]:
    """Log an incoming or outgoing message/interaction with a contact and record the timestamp.

    Args:
        contact_name_or_id: The contact's name or document ID.
        channel: The platform used (e.g. 'whatsapp', 'imessage', 'gmail', 'google_chat').
        message_text: The content or summary of the message.
        direction: Direction of communication, either 'received' or 'sent'. Defaults to 'received'.

    Returns:
        Confirmation dictionary with the interaction ID and updated contact timestamp.
    """
    contact = get_contact(contact_name_or_id)
    if "error" in contact:
        return contact

    db = _get_db()
    contact_id = contact["id"]
    timestamp = datetime.now(timezone.utc).isoformat()

    interaction_data = {
        "channel": channel.lower(),
        "message_text": message_text,
        "direction": direction.lower(),
        "timestamp": timestamp,
    }

    doc_ref = (
        db.collection("contacts")
        .document(contact_id)
        .collection("interactions")
        .document()
    )
    doc_ref.set(interaction_data)

    db.collection("contacts").document(contact_id).update({
        "last_interaction": timestamp,
    })

    return {
        "status": "success",
        "contact_id": contact_id,
        "contact_name": contact.get("name"),
        "interaction_id": doc_ref.id,
        "channel": channel.lower(),
        "direction": direction.lower(),
        "timestamp": timestamp,
    }


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are OmniCRM, an intelligent universal communication and relationship manager agent. "
        "You help users manage contacts and interactions across platforms like WhatsApp, iMessage, Gmail, and Google Chat. "
        "Your core capabilities: "
        "1. Lookup contacts and their cross-platform preferences (`list_contacts`, `get_contact`). "
        "2. Add or update contact profiles (`save_contact`). "
        "3. Continuously learn and refine per-platform communication styles (`update_contact_style`). "
        "4. Log messages and conversations across channels (`log_interaction`). "
        "5. Generate pre-recommended message drafts tailored to each person's preferred tone and platform norms (`draft_recommended_message`). "
        "When the user asks you to draft a message: "
        "- Retrieve the contact's profile and communication style for the requested platform. "
        "- Match their preferred tone (length, greeting, emoji usage, sign-offs). "
        "- Show the draft clearly labeled with the target platform and why this style was chosen."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        list_contacts,
        get_contact,
        save_contact,
        update_contact_style,
        log_interaction,
        draft_recommended_message,
    ],
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
