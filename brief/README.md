# Convențiile temei de proiectare

Fișierele din `brief/` sunt singura autoritate semantică pentru deciziile curente ale gospodăriei. Catalogul
[`budget/data/project.json`](../budget/data/project.json) este autoritatea operațională pentru costuri, includere,
responsabilitate, finalizare, tranșe și plăți, iar [`model/house.blend`](../model/house.blend) și sursele sale întreținute
descriu varianta geometrică acceptată. O stare contabilă, un preț sau o măsurătoare din model nu schimbă singure o
cerință a gospodăriei.

Toate înregistrările din acest șablon descriu gospodăria fictivă „Casa Exemplu” și sunt conținut demonstrativ, care se
înlocuiește cu deciziile proprii ale utilizatorului, păstrând convențiile de mai jos.

## Fișiere

- [Proiect](project.md): gospodărie, parcelă, limite bugetare și calendar.
- [Arhitectură](architecture.md): amplasare, formă, program, topologie, circulații și acustică.
- [Încăperi și mobilare](rooms-and-furnishings.md): funcțiuni, mobilier, electrocasnice și obiecte sanitare.
- [Interioare](interiors.md): stil, finisaje, materiale și atmosfera luminii.
- [Sisteme](systems.md): climatizare, ventilare, apă, energie, monitorizare și punere în funcțiune.
- [Casă inteligentă](smart-home.md): comenzi, automatizare, confidențialitate și securitate.
- [Exterior](outdoor.md): grădină, terasă, acces, parcare și împrejmuire.
- [Bunuri existente](existing-assets.md): inventarul de reutilizat și cerințele de integrare.
- [Referințe](references.md): surse normative, tehnice și de inspirație.

## Etapele de finalizare

În toate fișierele tematice, cerințele sunt grupate în aceeași ordine:

1. `La roșu` — rezultatul este stabilit sau realizat până la închiderea structurii și anvelopei.
2. `La gri` — traseele, suporturile, dozele, golurile și celelalte pregătiri ascunse sunt executate.
3. `La cheie` — sistemul, finisajul sau dotarea fixă este instalată, funcțională și recepționată.
4. `La mutat` — bunurile mobile și configurațiile de utilizare sunt prezente la mutarea familiei.
5. `Extra` — angajamentele acceptate pentru perioada de după mutare sunt finalizate.

Etapa exprimă momentul până la care rezultatul trebuie să fie complet, nu momentul plății. O pregătire anterioară
apare separat numai când are un rezultat verificabil propriu. Necunoscutele tehnice rămân lângă cerința pe care o
condiționează și se rezolvă prin proiect, studii, oferte sau punere în funcțiune; ele nu sunt mutate automat în
`Extra`. Înregistrările din introducerea unui fișier pot să nu aibă etapă.

## Înregistrări și ID-uri

Deciziile folosesc tabele `ID | Decizie`. ID-urile sunt stabile, nu se renumerotează și nu se reutilizează după
retragere. Un fișier care nu deține decizia citează linkul și ID-ul proprietarului semantic în loc să o repete.
Tabelele de inventar, topologie sau geometrie pot păstra coloanele suplimentare strict necesare.

Toate direcțiile consemnate sunt decizii acceptate; flexibilitatea reală, alegerea de produs și verificările încă
deschise sunt scrise direct în decizie, nu codificate ca stare a înregistrării. Când gospodăria acceptă o decizie
nouă, înregistrările afectate se actualizează pe loc, fără a păstra variantele înlocuite.

## Geometrie și sincronizare

Tema păstrează programul, relațiile și limitele acceptate. Măsurătorile detaliate ale variantei curente rămân dovezi
ale modelului conform [`model/AGENTS.md`](../model/AGENTS.md); cantitățile de cost rămân în catalogul bugetar.
Reconciliați tema, catalogul și modelul la acceptarea unei schimbări; ele pot rămâne temporar nesincronizate între
commit-uri, dar un preț, o stare bugetară sau o măsurătoare din model nu schimbă singure o cerință a gospodăriei.

Dimensiunile nominale comunică intenția; diferențele subdecimetrice se consemnează numai dacă afectează plafonul de
180 m², retragerea de 2 m, programul sau conexiunile.

## Limbă și dovezi

Proza din `brief/` este în română, cu terminologie românească de arhitectură, construcții și instalații. Preferințele
gospodăriei, inspirațiile, cerințele legale, recomandările specialiștilor și necunoscutele proiectului rămân distincte.
Regulile dimensionale și de conformare citează legislația, normativele și standardele românești aplicabile.
Reglementările urbanistice locale rămân necunoscute ale proiectului până la emiterea certificatului de urbanism.
Datele parcelei, conformarea, performanța și costurile se validează de profesioniștii responsabili pe proiectul real.
