import React, { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import DataSearch from './components/DataSearch';

const root = createRoot(document.getElementById('data-search'));
root.render(<StrictMode><DataSearch /></StrictMode>);
