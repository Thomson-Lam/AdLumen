import together

API_KEY = "78623dc87eba15873654310f371ee2c5f8b4f5b732276ae5204a45bd1a60c107"

client = together.Together(api_key=API_KEY)

response = client.chat.completions.create(
    model="mistralai/Mixtral-8x7B-Instruct-v0.1",
    messages=[
        {"role": "user", "content": "Write a cybersecurity report about a suspicious website."}
    ],
    max_tokens=300,
    temperature=0.7,
)

print(response.choices[0].message.content)
