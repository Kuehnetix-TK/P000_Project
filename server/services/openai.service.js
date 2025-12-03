// server/services/openai.service.js
import OpenAI from 'openai';
import dotenv from 'dotenv';
dotenv.config();

const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

export async function chat(messages) {
  const response = await client.chat.completions.create({
    model: 'gpt-4.1-mini',   // oder was eure Schule zulässt
    messages,
    temperature: 0.1
  });

  return response.choices[0].message;
}
