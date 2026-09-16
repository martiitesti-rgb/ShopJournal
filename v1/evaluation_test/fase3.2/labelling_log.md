## Log della seconda parte della fase 3

Durante lo sviluppo del sistema di raccomandazione è stato identificato e corretto un bug nel pre-filtro dei candidati (mancava l'ordinamento per rilevanza dei match, ho aggiunto un count match come quello utilizzato in build_pool, causando un tetto arbitrario di 200 candidati non ordinati); dopo la correzione, i candidati generati sono risultati sostanzialmente più pertinenti, secondo il mio parere anche troppo pertinenti. Infatti non c'è molta diversificazione egli scoring in molti casi sono tutti buoni. 

Addirittura nella query 9  e 5 ci sono prodotti praticamente uguali, che si distinguono per dei particolari. Questo è un limite del sistema attuale.

Per quanto rigurarda la q10 in tabella ci sono solamente prodotti che fanno riferimento a ciò che dice la nota e non la query attuale. Questo evidenzia un limite strutturale di `matchNotes()`: le note derivate dallo storico
d'acquisto sono un segnale utile quando c'è continuità tematica tra query e abitudini
pregresse dell'utente, ma possono introdurre rumore quando l'utente cerca qualcosa che si
discosta dal suo storico tipico