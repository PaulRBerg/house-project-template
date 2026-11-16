# Sisteme

Acest fișier deține rezultatele pentru climatizare, ventilare, apă, energie, monitorizare și exploatare. Dimensionarea,
alegerea echipamentelor și conformarea se stabilesc prin proiectele de specialitate; comenzile sunt definite în
[Casă inteligentă](smart-home.md).

| ID      | Decizie                                                                                                                                                                                                                                                                                                                                          |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `EN-01` | Strategia de casă sănătoasă și eficientă prioritizează anvelopa performantă și etanșă, controlul surselor de poluare, ventilarea silențioasă cu recuperare de căldură, controlul umidității și exploatarea simplă. Conformarea nZEB conform Mc 001-2022 este minimul legal (`SITE-08`); casa nu folosește gaze naturale sau combustibili solizi. |

## La roșu

Golurile structurale, spațiile tehnice și traseele principale sunt rezervate și verificate pentru pompa de căldură,
MVHR, coloanele sanitare, cablurile fotovoltaice și racordurile utilităților.

## La gri

| ID      | Decizie                                                                                                                                                                                                                                                                                                                                                                                                            |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `EN-02` | Băile suprapuse (`G-BATH`, `U-BATH`) și camera tehnică folosesc o zonă comună de coloane sanitare și trasee verticale de ventilare, cu lungimi scurte și acces pentru revizie. Tubulatura MVHR, conductele încălzirii în pardoseală și traseele electrice se pozează și se verifică înaintea șapelor și tencuielilor.                                                                                              |
| `EN-08` | Casa se racordează la rețelele publice de apă și de canalizare menajeră, dacă există în zonă; disponibilitatea lor și a rețelei electrice se confirmă prin certificatul de urbanism și avizele administratorilor. Racordurile și căminele de pe parcelă se execută într-o singură campanie cu traseele exterioare (`GAR-06`), conform I9-2022 pentru instalațiile sanitare și normativelor de branșare aplicabile. |

## La cheie

### Climatizare și apă

| ID      | Decizie                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `EN-03` | Sursa unică de încălzire este o pompă de căldură aer–apă, cu distribuție prin încălzire în pardoseală pe ambele niveluri. Unitatea exterioară stă pe latura de servicii, cu debit de aer, condens, mentenanță și acustică rezolvate prin proiect, departe de ferestrele dormitoarelor. Răcirea de vară se asigură prin protecție solară exterioară și, dacă calculul o justifică, prin răcire în pardoseală cu control al punctului de rouă. |
| `EN-04` | Apa caldă menajeră se prepară de pompa de căldură într-un boiler de circa 200 l amplasat în camera tehnică, cu protecție antilegionella programată; volumul se verifică după consumul familiei.                                                                                                                                                                                                                                              |
| `EN-09` | Apa pluvială de pe acoperiș se colectează prin receptoare și burlane ascunse sau pe fațadele secundare și se evacuează pe parcelă sau la rețea conform proiectului, fără stocare pentru reutilizare.                                                                                                                                                                                                                                         |

### Ventilare și recepție

| ID      | Decizie                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `EN-05` | MVHR este complet și funcțional ca instalație centralizată dublu flux echilibrat: unitate în camera tehnică, introducere filtrată în dormitoare, birou și living, evacuare din bucătărie, băi și camera tehnică, cu tubulatură, atenuatoare acustice și guri coordonate. Schimbătorul de bază este sensibil, în contracurent; aerul exterior este filtrat cel puțin ePM1 conform ISO 16890. Debitele se dimensionează conform I5-2022, cu EN 16798-1 categoria II ca reper. |
| `EN-06` | La recepție se măsoară și se echilibrează debitul fiecărei guri MVHR, se verifică zgomotul în dormitoare și se consemnează rezultatele, reglajele și programul de mentenanță al filtrelor.                                                                                                                                                                                                                                                                                  |
| `EN-10` | Sistemele se predau cu documentație clară de exploatare, reglaj, consumabile și garanții, iar echipamentele rămân accesibile pentru întreținere și înlocuire.                                                                                                                                                                                                                                                                                                               |

### Energie

| ID      | Decizie                                                                                                                                                                                                                                                                                                      |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `EN-07` | Pe acoperișul terasă se montează un sistem fotovoltaic racordat la rețea, cu invertor compatibil cu o baterie ulterioară, dimensionat după consumul estimat al casei și suprafața disponibilă în spatele aticelor. Lestarea, încărcările din vânt și zăpadă și înălțimea modulelor se verifică prin proiect. |

## La mutat

| ID      | Decizie                                                                                                                                                                                                                   |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `EN-11` | Dormitoarele și livingul au monitorizare a CO₂, temperaturii și umidității, folosită de automatizarea ventilării (`TECH-06`). CO₂ este numai un indicator indirect al ventilării, nu dovada calității generale a aerului. |

## Extra

| ID      | Decizie                                                                                                                                                                               |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `EN-12` | După un an de date de consum și producție se evaluează adăugarea unei baterii de stocare în invertorul pregătit la `EN-07`; capacitatea se dimensionează din profilul real de consum. |
