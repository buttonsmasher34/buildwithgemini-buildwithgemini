"""Seed script for OmniCRM Firestore database."""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-9dceb0c15b1a"

SAMPLE_CONTACTS = [
    {
        "id": "alex_chen",
        "name": "Alex Chen",
        "relationship": "Colleague / Tech Lead",
        "channels": ["google_chat", "gmail", "whatsapp"],
        "preferred_channel": "google_chat",
        "tone_preference": "concise, technical, direct, infrequent emojis",
        "communication_style": {
            "google_chat": "Quick bullet points, code snippets, lowercase informal greetings like 'hey alex'",
            "gmail": "Structured with action items and context links",
            "whatsapp": "Casual, fast confirmations"
        },
        "notes": "Prefers quick asynchronous updates before 10 AM. Working on backend API migrations.",
        "last_interaction": "2026-10-07T16:30:00Z"
    },
    {
        "id": "sarah_miller",
        "name": "Sarah Miller",
        "relationship": "Client / Product Manager",
        "channels": ["gmail", "imessage"],
        "preferred_channel": "gmail",
        "tone_preference": "professional, warm, enthusiastic, polite sign-offs",
        "communication_style": {
            "gmail": "Proper greeting ('Hi Sarah'), appreciative tone, clear milestone tracking, signature",
            "imessage": "Brief check-ins, friendly with occasional thumbs-up or smileys"
        },
        "notes": "Always highlight user impact and deadlines. Appreciates proactive status updates on Thursdays.",
        "last_interaction": "2026-10-06T19:15:00Z"
    },
    {
        "id": "marcus_vance",
        "name": "Marcus Vance",
        "relationship": "Close Friend & Collaborator",
        "channels": ["whatsapp", "imessage"],
        "preferred_channel": "whatsapp",
        "tone_preference": "casual, conversational, humor-friendly, voice notes or rapid texts",
        "communication_style": {
            "whatsapp": "Casual slang, meme references, short 1-line thoughts, lots of emojis",
            "imessage": "Photo sharing, weekend plan coordination"
        },
        "notes": "Catch up about weekend hackathons and gym progress. Prefers evening messages.",
        "last_interaction": "2026-10-08T14:10:00Z"
    }
]


def seed_database():
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("contacts")

    for contact in SAMPLE_CONTACTS:
        contact_id = contact["id"]
        data = {k: v for k, v in contact.items() if k != "id"}
        collection_ref.document(contact_id).set(data)
        print(f"Seeded contact: {contact['name']} (ID: {contact_id})")

    print("\nFirestore seeding complete!")


if __name__ == "__main__":
    seed_database()
