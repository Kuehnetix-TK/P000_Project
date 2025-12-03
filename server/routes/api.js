// server/routes/api.js
import { Router } from 'express';
import { generateSQLAndExecute } from '../services/sql-generator.service.js';

const router = Router();

router.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

router.post('/query', async (req, res) => {
  try {
    const { query } = req.body;
    const result = await generateSQLAndExecute(query);
    res.json(result);
  } catch (err) {
    console.error(err);
    res.status(500).json({ status: 'error', message: err.message });
  }
});

export default router;
