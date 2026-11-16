# Casă inteligentă

Acest fișier deține comenzile, automatizarea, confidențialitatea și securitatea. Tehnologia rămâne discretă,
întreținabilă și sub controlul familiei.

| ID        | Decizie                                                                                                                                                                                                                  |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `TECH-01` | Funcțiile esențiale (iluminat, încălzire, ventilare, jaluzele, acces) rămân locale și funcționează fără internet sau cloud. Fiecare încăpere are comenzi fizice pentru lumină, iar automatizările pot fi anulate manual. |
| `TECH-02` | Familia deține și controlează acreditările, configurațiile și datele. La predare primește proiectul de automatizare, configurațiile, parolele de administrare și copiile de siguranță.                                   |

## La roșu

Spațiile tehnice, golurile și rutele principale sunt rezervate pentru tablouri, magistrala cablată, rețea, acces și
securitate.

## La gri

| ID        | Decizie                                                                                                                                                                                                                                                                                                                                                                 |
| --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TECH-03` | Rețeaua de date Cat 6A deservește toată casa în topologie stea, către punctul central din camera tehnică (`RM-TECH-01`), cu puncte în fiecare încăpere, puncte în tavan pentru AP-uri Wi-Fi și legături la poarta pietonală și la camerele exterioare. Se rezervă tuburi goale cu șnur de tragere către fiecare nivel și spre exterior, pentru înlocuiri fără demolări. |
| `TECH-04` | Se execută magistrala KNX cablată pentru iluminat, jaluzele, termostatele pe camere, senzori și contacte la deschideri, cu doze și trasee coordonate cu mobilierul fix.                                                                                                                                                                                                 |

## La cheie

### Control și automatizare

| ID        | Decizie                                                                                                                                                                                                                                                                                           |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TECH-05` | Temperatura se controlează pe camere, cu actuatoare la distribuitoarele încălzirii în pardoseală și integrarea pompei de căldură din [Sisteme](systems.md) (`EN-03`). Modurile de confort sunt Comfort, Eco, Away și Night; protecțiile echipamentelor rămân în automatizarea proprie a acestora. |
| `TECH-06` | Integrarea MVHR reglează debitul după CO₂ și umiditate, activează regimul intensificat în băi și bucătărie și gestionează bypass-ul de vară, fără a anula debitul minim necesar (`EN-05`, `EN-11`).                                                                                               |
| `TECH-07` | Jaluzelele exterioare din [Arhitectură](architecture.md) (`SITE-09`) se comandă individual și pe fațade, automat după soare pentru limitarea supraîncălzirii, cu protecție automată la vânt prin stație meteo.                                                                                    |

### Confidențialitate și securitate

| ID        | Decizie                                                                                                                                                                                                                                                                |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TECH-08` | Nu există camere video sau microfoane permanente în interior. Camerele exterioare acoperă numai accesul și parcela proprie, fără a filma proprietăți vecine sau domeniul public dincolo de necesar, iar înregistrările rămân local.                                    |
| `TECH-09` | Detectoarele de fum au alarmare locală autonomă și notificări integrate; senzorii de scurgere din băi, bucătărie și camera tehnică închid automat electrovalva principală de apă. Prevederile de detecție aplicabile se stabilesc de specialiști conform P 118/1-2025. |
| `TECH-10` | Poarta pietonală are video-interfon cablat, iar ușa de intrare are yală electrică cu cod și smartphone, cu cheie mecanică de rezervă.                                                                                                                                  |

## La mutat

| ID        | Decizie                                                                                                                                                         |
| --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TECH-11` | Rețeaua Wi-Fi, aplicația unică de control și scenele de bază (Home, Away, Night) sunt configurate și explicate întregii familii, inclusiv copilului, la mutare. |

## Extra

Extinderile ulterioare folosesc magistrala, rețeaua și regulile de control existente, fără să înlocuiască comenzile
fizice sau funcționarea locală (`TECH-01`).
