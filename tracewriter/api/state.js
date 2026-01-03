import { kv } from '@vercel/kv';

const STATE_KEY = 'tracewriter:state';

export default async function handler(req, res) {
  // Set CORS headers for local development
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  try {
    if (req.method === 'GET') {
      const state = await kv.get(STATE_KEY);
      return res.status(200).json(state || { properties: [], annotations: {} });
    }

    if (req.method === 'POST') {
      const { properties, annotations } = req.body;

      if (!properties || !annotations) {
        return res.status(400).json({ error: 'Missing properties or annotations' });
      }

      await kv.set(STATE_KEY, { properties, annotations });
      return res.status(200).json({ success: true, savedAt: new Date().toISOString() });
    }

    return res.status(405).json({ error: 'Method not allowed' });
  } catch (error) {
    console.error('State API error:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
}
