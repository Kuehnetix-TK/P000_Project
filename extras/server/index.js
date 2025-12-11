// server/index.js
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
import apiRoutes from './routes/api.js';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(helmet());
app.use(cors());
app.use(express.json());

// statisches Frontend
app.use(express.static('public'));

// API-Routen
app.use('/api', apiRoutes);

app.listen(PORT, () => {
  console.log(`Server läuft auf http://localhost:${PORT}`);
});
