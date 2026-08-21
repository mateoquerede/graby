"""Coto product search through the public search API."""


def search_product(client, query):
    print(f"🔎 Searching: {query}")
    payload = client.search(query)
    print("✅ Results loaded")
    return payload