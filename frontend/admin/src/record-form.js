import React from 'react';
import { createRoot } from 'react-dom/client';

import GazetterSelector from './components/GazetterSelector';
// Render your React component instead
const recordElem = document.getElementById('record-id');
const root = createRoot(document.getElementById('my-gazetter'));
root.render(<GazetterSelector recordId={recordElem.value}/>);

