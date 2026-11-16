# Diagrama intențiilor pentru casă

Aceasta este o reprezentare compactă a relațiilor obligatorii dintre încăperi din tema demonstrativă. Nu este un plan, o
geometrie cotată, o orientare cardinală sau un proiect aprobat. Arhitectul poate oglindi sau roti organizarea pentru
terenul real, păstrând topologia consemnată în [`brief/architecture.md`](brief/architecture.md) (`LAY-01`).

```mermaid
flowchart TB
  Street["Strada · latura 1–2<br/>poartă pietonală · poartă auto"] --> Parking["Loc de parcare descoperit<br/>un autoturism"]
  Street --> Hall["Hol de intrare<br/>haine și încălțăminte"]
  Hall --> Living["Living și dining<br/>masă pentru șase"]
  Living -->|gol deschis| Kitchen["Bucătărie<br/>front liniar + peninsulă"]
  Hall --> Office["Birou / cameră de oaspeți<br/>canapea extensibilă"]
  Hall --> GroundBath["Baie parter<br/>duș · WC · lavoar"]
  Hall --> Tech["Cameră tehnică și spălătorie<br/>pompă de căldură · ACM · MVHR"]
  Hall --> Stair["Scară<br/>două rampe drepte egale · podest"]
  Living -->|ușă vitrată| Terrace["Terasă descoperită"]
  Terrace --> Garden["Grădină<br/>gazon · câțiva pomi · arbuști"]

  Stair --> Lobby["Hol etaj"]
  Lobby --> MainBed["Dormitor matrimonial<br/>pat 160 × 200 cm"]
  Lobby --> ChildBed["Camera copilului"]
  Lobby --> UpperBath["Baie etaj<br/>cadă/duș · WC · lavoar"]
```

Casa demonstrativă este P+1, fără subsol, cu amprentă de concept de circa 10,0 × 8,0 m și un plafon de 180 m²
construiți desfășurați, inclusiv finisajele. Parcela fictivă are circa 24 × 40 m (circa 960 m²); conceptul păstrează
minimum 2 m față de toate limitele pentru casă, terasă și proiecțiile acoperișului. Orientarea și geometria reală se
stabilesc după ridicarea topografică și certificatul de urbanism.
