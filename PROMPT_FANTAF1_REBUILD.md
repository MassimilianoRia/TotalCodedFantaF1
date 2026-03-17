# Prompt generale — Ricostruzione completa FantaF1 da zero

Voglio che tu progetti e implementi da zero un'applicazione completa per un gioco fantasy ispirato alla Formula 1, chiamata **FantaF1**.

## Mandato

Non devi partire da codice esistente, né da uno schema database predefinito, né da una specifica tecnica già vincolante.
Devi invece:

- analizzare il dominio;
- ricostruire i requisiti funzionali;
- proporre un'architettura coerente;
- scegliere liberamente stack, linguaggi, database e organizzazione del progetto;
- implementare una soluzione pulita, estendibile e realmente usabile.

Puoi scegliere tecnologie diverse da web + Supabase se ritieni esistano alternative migliori.
La priorità è rispettare regole di gioco, flussi utente e logica di punteggio descritte qui sotto.

---

## 1) Obiettivo del prodotto

Il prodotto è un sistema fantasy F1 multiutente in cui:

- esistono piloti reali e costruttori reali;
- esistono team fantasy creati nel sistema;
- ogni utente registrato può controllare un solo team fantasy;
- ogni team fantasy possiede 5 piloti;
- durante ogni weekend di gara gli utenti possono:
  - fare predizioni,
  - scegliere un capitano tra i propri piloti,
  - partecipare a un minigioco separato;
- a weekend concluso il sistema importa o registra i risultati reali;
- il sistema calcola:
  - punti di ogni pilota fantasy per quel weekend,
  - punti del team fantasy per quel weekend,
  - classifica generale stagionale,
  - statistiche e breakdown dettagliati;
- alcuni weekend sono con sprint, altri no;
- i weekend diventano “ufficiali” solo quando vengono finalizzati.

L'app deve essere pensata per un piccolo gruppo di utenti reali, non come demo finta.

---

## 2) Filosofia di implementazione

Hai libertà di progettazione, ma devi seguire questi principi:

- non riciclare una struttura esistente;
- non limitarti a tradurre regole in tabelle;
- costruisci un sistema coerente a livello di:
  - dominio,
  - modelli,
  - persistenza,
  - servizi,
  - API,
  - UI (se prevista);
- separa bene:
  - dati sorgente dei risultati reali,
  - regole di scoring,
  - dati materializzati o cache,
  - viste/read model per frontend;
- prevedi un modo robusto di:
  - ricalcolare un weekend,
  - verificare consistenza dei dati importati,
  - gestire correzioni post-gara;
- privilegia chiarezza, coerenza e tracciabilità delle regole.

Se devi fare trade-off, spiegali.

---

## 3) Concetti fondamentali del dominio

Il sistema deve modellare almeno questi concetti (con la rappresentazione che ritieni più adatta):

- costruttori
- piloti
- team fantasy
- utenti
- associazione utente ↔ team fantasy
- weekend di gara
- risultati di qualifica
- risultati sprint
- risultati gara
- eventi del weekend non derivabili automaticamente
- predizioni utente
- capitano del weekend
- punteggi pilota per weekend
- punteggi team per weekend
- classifica cumulativa
- minigioco separato del weekend

---

## 4) Regole funzionali del gioco

### 4.1 Team fantasy

- Ogni team fantasy ha **esattamente 5 piloti**.
- Ogni utente può controllare **un solo team fantasy**.
- Ogni team fantasy può essere controllato da **un solo utente**.
- Puoi decidere se il roster è fisso o modificabile, ma nella base considera il roster definito e disponibile al calcolo.

### 4.2 Weekend

Ogni weekend ha:

- nome
- stagione
- round
- informazione sprint sì/no
- apertura predizioni
- chiusura predizioni
- fine weekend
- stato di finalizzazione ufficiale

Il sistema deve distinguere chiaramente:

- stato temporale del weekend
- stato ufficiale di validazione/finalizzazione

La classifica generale deve sommare solo i weekend finalizzati.

### 4.3 Predizioni utente

- Ogni utente può fare **una sola scheda predizioni per weekend**.
- Le predizioni sono modificabili/eliminabili solo prima della chiusura predizioni.

Predizioni da supportare:

- booleane:
  - ci sarà bandiera rossa?
  - ci sarà safety car o virtual safety car?
  - verranno usate gomme da bagnato?
  - i primi due classificati apparterranno allo stesso costruttore?
  - chi parte in pole vincerà la gara?
  - ci saranno più di 2 ritiri/non classificati rilevanti?
- numerica discreta:
  - quante scuderie porteranno entrambi i piloti in top 10 (0..5)

Punteggi predizioni:

- bandiera rossa
  - sì e succede: +7
  - no e non succede: +5
- safety car / VSC
  - corretto: +3
- gomme da bagnato
  - corretto: +2
- primi due stesso costruttore
  - corretto: +4
- poleman vincitore
  - sì e succede: +2
  - no e non succede: +4
- più di 2 DNF/DNS
  - corretto: +5
- numero costruttori con entrambi in top 10 (solo se esatto)
  - 0 -> +10
  - 1 -> +8
  - 2 -> +6
  - 3 -> +5
  - 4 -> +5
  - 5 -> +6

Alcune predizioni dipendono da eventi manuali/non derivabili automaticamente:

- distingui eventi derivabili da risultati vs eventi manuali;
- se un evento manuale manca, non assegnare punti arbitrari.

### 4.4 Eventi del weekend non derivabili automaticamente

Per ogni weekend possono essere registrati manualmente:

- bandiera rossa sì/no
- safety car o VSC sì/no
- gomme da bagnato sì/no
- Driver of the Day

Questi eventi devono influenzare il calcolo punteggi.

### 4.5 Capitano del weekend

- Ogni utente può scegliere un solo capitano tra i 5 piloti del proprio team per uno specifico weekend.
- Vincoli:
  - il capitano deve appartenere al team dell'utente;
  - può essere impostato/modificato/rimosso solo fino alla chiusura predizioni.
- Effetto:
  - il capitano raddoppia tutti i punti del pilota (bonus e malus inclusi).

---

## 5) Regole di punteggio pilota

Il sistema deve calcolare i punti di ogni pilota fantasy per weekend.

### 5.1 Gara principale

- P1=25, P2=18, P3=15, P4=12, P5=10, P6=8, P7=6, P8=4, P9=2, P10=1, oltre=0
- Solo per pilota classificato.

### 5.2 Sprint (se presente)

- P1=8, P2=7, P3=6, P4=5, P5=4, P6=3, P7=2, P8=1
- Se weekend senza sprint: 0.

### 5.3 Qualifica

- pole +5
- posizioni 2-5: +3
- posizioni 6-10: +2
- posizioni 11-16: +1
- oltre: 0

### 5.4 Delta posizioni gara

Per piloti classificati:

- `(posizione_partenza - posizione_finale) * 0.5`
- guadagno = bonus, perdita = malus.

### 5.5 Duello col compagno

Regola:

- niente compagno valido: 0
- pilota non classificato: 0
- pilota classificato e compagno non classificato: +1
- entrambi classificati:
  - pilota davanti al compagno: +2
  - altrimenti: -1

### 5.6 Penalità gara

- penalità in gara: -5

### 5.7 Stato gara

- DNF o DNS: -10
- DSQ: -15

### 5.8 Driver of the Day

- se il pilota è Driver of the Day reale: +3

### 5.9 Bonus ultimi classificati

Tra i piloti classificati:

- ultimo classificato: +10
- penultimo classificato: +5

Gestire correttamente anche scenari con ritiri multipli.

---

## 6) Regole punteggio team fantasy

Per ogni weekend:

- totale team = somma punti dei 5 piloti + punti predizioni utente;
- se esiste capitano, i suoi punti pilota valgono doppio;
- se team non claimato, contributo predizioni = 0.

---

## 7) Risultati reali da gestire

Il sistema deve gestire almeno:

- **Qualifica**: posizione qualifica per pilota
- **Sprint**: posizione sprint per pilota
- **Gara**:
  - posizione di partenza ufficiale
  - posizione finale se classificato
  - stato gara: `classified`, `dnf`, `dns`, `dsq`
  - flag penalità in gara

Il numero di piloti attivi può cambiare: evita hardcode non necessari.

---

## 8) Validazione e preflight

Serve una logica robusta prima del recompute weekend. Deve verificare almeno:

- weekend esistente
- risultati gara presenti in quantità coerente coi piloti attivi previsti
- risultati sprint presenti se weekend con sprint
- assenza di duplicati nelle posizioni dove non ammessi
- coerenza stato gara vs posizione finale
- consistenza griglia/finish
- (opzionale) consistenza piloti per costruttore
- completezza minima per calcolo affidabile

Strategia libera (fail-fast, strict/non-strict, validator separato, pipeline), ma workflow chiaro.

---

## 9) Recompute e materializzazione

Il sistema deve poter:

- ricalcolare punti pilota di un singolo weekend
- ricalcolare punti team di un singolo weekend
- ricalcolare tutto il weekend in modo orchestrato
- opzionalmente ricalcolare stagione/intero storico

Scegli e motiva: materializzazione, on-demand, cache, read model/projection.

Vincoli: consistenza, spiegabilità, efficienza ragionevole, facilità di correzione.

---

## 10) Statistiche, recap e breakdown

Deve essere possibile mostrare via UI o API:

### Per weekend e pilota

Breakdown dettagliato:

- punti gara
- punti sprint
- punti qualifica
- delta posizioni
- duello teammate
- penalità
- malus DNF/DNS
- malus DSQ
- Driver of the Day
- bonus ultimo/penultimo
- totale

### Per team fantasy e weekend

- totale punti piloti
- totale punti predizioni
- totale weekend
- cumulata stagionale (solo weekend finalizzati)

Dettaglio piloti del team:

- breakdown completo
- totale effettivo
- indicazione capitano

### Classifica generale

Per tutti i team fantasy:

- punteggio totale su weekend finalizzati
- eventuale punteggio minigioco separato

---

## 11) Minigioco separato (“poop trophy”)

Regole:

- per ogni weekend esiste una mini-squadra casuale di 5 piloti;
- ogni utente predice in quale bucket cadrà il totale della mini-squadra:
  - `<= 40`
  - `41..80`
  - `> 80`
- a weekend finalizzato:
  - si calcola il totale reale mini-squadra,
  - si determina bucket corretto,
  - ogni utente che indovina ottiene 1 punto speciale “poop trophy”.

Vincoli:

- non entra nei punti fantasy principali;
- deve comparire in leaderboard accessoria;
- una sola previsione minigioco per utente/weekend;
- previsione modificabile/eliminabile solo fino alla chiusura predizioni;
- mini-squadra unica per weekend e non incompleta.

---

## 12) Esperienza utente attesa

Non imponiamo frontend specifico, ma i flussi devono essere realisticamente supportati.

### Utente

- autenticarsi
- vedere il proprio team e i 5 piloti
- vedere weekend attuale/aperto
- inviare/cancellare predizioni
- scegliere/rimuovere capitano
- partecipare al minigioco
- consultare classifica generale
- vedere recap punti dettagliato
- vedere storico weekend-by-weekend

### Admin o sistema

- creare/aggiornare weekend
- inserire/importare risultati
- inserire eventi manuali weekend
- eseguire validation/preflight
- eseguire recompute
- finalizzare weekend

Puoi proporre ruoli admin specifici.

---

## 13) Libertà architetturale

Puoi scegliere liberamente:

- monolite o modulare
- REST / GraphQL / RPC / CLI / event-driven
- SQL / NoSQL / mista
- frontend web/app/desktop/CLI oppure solo API (se motivato)
- materialized views, aggregate tables, CQRS, domain service, ecc.

Prima di implementare, proponi un'architettura motivata e il trade-off scelto.

---

## 14) Deliverable richiesti

### Fase 1 — Analisi

- ricostruzione dominio
- entità/relazioni/flussi/invarianti
- ambiguità e decisioni progettuali
- proposta architetturale

### Fase 2 — Progettazione

- modello dati/dominio
- servizi e casi d'uso
- punti di calcolo scoring
- strategia recompute
- gestione read model/statistiche/leaderboard

### Fase 3 — Implementazione

- sistema completo
- motore scoring
- minigioco
- operazioni utente
- flussi admin/sistema
- test regole principali

### Fase 4 — Consegna

- struttura progetto
- file principali
- spiegazione scelte
- istruzioni avvio
- seed/esempi dati
- esempio weekend completo con recompute

---

## 15) Vincoli qualitativi

La soluzione deve essere:

- coerente
- leggibile
- non improvvisata
- debuggabile
- con scoring centralizzato
- con ricalcolo affidabile
- con separazione chiara tra dati sorgente e risultati calcolati
- mantenibile da una persona o piccolo team

Evita:

- overengineering
- dipendenze inutili
- magic numbers sparsi
- logica scoring duplicata
- accoppiamento eccessivo UI ↔ dominio

---

## 16) Punto cruciale

Non voglio una semplice CRUD app con formule sparse.
Voglio un sistema in cui il cuore sia il **motore di regole del fantasy F1**, con storico, recalcolo, predizioni, capitano, minigioco e recap dettagliato.

Progetta come se dovessi consegnare una prima versione davvero usabile e difendibile tecnicamente.
