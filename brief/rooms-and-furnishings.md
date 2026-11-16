# Încăperi și mobilare

Acest fișier deține funcțiile încăperilor, mobilierul, electrocasnicele, obiectele sanitare și condițiile de utilizare;
pozițiile și legăturile dintre spații sunt definite în [Arhitectură](architecture.md) (`LAY-01`).

| ID            | Decizie                                                                                                                                                                                                                                                                                                                                                                                                     |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RM-HOUSE-01` | Casa are exact două dormitoare permanente (`U-MBED`, `U-CHILD`), o cameră de birou folosită și pentru oaspeți (`G-OFF`) și două băi complete (`G-BATH`, `U-BATH`), toate accesibile din circulații. Nu se adaugă alte camere de dormit.                                                                                                                                                                     |
| `RM-LIV-01`   | Livingul susține mesele în familie și cu oaspeți, relaxarea, lectura și consumul media comun. Zona de dining are o masă pentru șase persoane, iar zona de șezut o canapea orientată spre peretele media, cu vedere spre terasă.                                                                                                                                                                             |
| `RM-KIT-01`   | Bucătăria are un front liniar de mobilier cu chiuvetă, plită cu inducție, cuptor, hotă cu evacuare sau recirculare stabilită prin proiectul de ventilare, frigider combinat integrat și mașină de spălat vase, plus o peninsulă sau insulă cu blat de lucru și două locuri pentru mic dejun. Electrocasnicele sunt alese pentru eficiență energetică și zgomot redus; modelele finale se aleg la achiziție. |
| `RM-OFF-01`   | Biroul Adultului A are un post de lucru orientat spre fereastră, depozitare închisă pentru documente și o canapea extensibilă pentru oaspeți, care lasă liber gabaritul de manevră al scaunului de lucru când este deschisă. Încăperea are prize și date suficiente pentru lucrul de acasă și apeluri video fără zgomot din living.                                                                         |
| `RM-MBED-01`  | Dormitorul matrimonial permite un pat de 160 × 200 cm cu acces pe ambele laturi, noptiere și un dulap pe toată înălțimea; se folosește numai pentru somn și odihnă, fără televizor.                                                                                                                                                                                                                         |
| `RM-CHILD-01` | Camera copilului permite un pat de o persoană, un birou de studiu, un dulap și spațiu liber pentru joacă pe pardoseală; mobilierul poate fi înlocuit pe măsură ce copilul crește, fără modificarea încăperii.                                                                                                                                                                                               |

## La roșu

Compartimentarea materializează programul de camere și lasă gabaritele necesare mobilării, obiectelor sanitare și
echipamentelor tehnice, inclusiv căile de înlocuire a acestora.

## La gri

| ID          | Decizie                                                                                                                                    |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `RM-LIV-02` | Peretele media din living primește suport pentru televizor, alimentare, Ethernet, cablare ascunsă și ventilare pentru echipamentele media. |

Alimentările, scurgerile și dozele pentru electrocasnicele din bucătărie, obiectele sanitare și echipamentele din
camera tehnică se execută după planurile de mobilare, înaintea tencuielilor.

## La cheie

### Intrare, bucătărie și servicii

| ID           | Decizie                                                                                                                                                                                                                                                                                                                                                                              |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `RM-HALL-01` | Holul de intrare are un dulap încastrat pentru hainele de sezon, un pantofar, o bancă pentru încălțat și cârlige pentru hainele zilnice, fără a reduce lățimea de circulație din `LAY-05`.                                                                                                                                                                                           |
| `RM-KIT-02`  | Mobilierul bucătăriei și electrocasnicele din `RM-KIT-01` sunt instalate și funcționale, cu fronturi mate, blat rezistent și iluminat de lucru sub corpurile suspendate.                                                                                                                                                                                                             |
| `RM-TECH-01` | Camera tehnică găzduiește unitatea interioară a pompei de căldură, boilerul ACM, unitatea MVHR, tabloul electric și punctul central de rețea, precum și mașina de spălat și uscătorul suprapuse, un blat pentru împăturit și o scurgere în pardoseală. Gabaritele de mentenanță și înlocuire ale echipamentelor rămân libere; ventilarea încăperii se dimensionează conform I5-2022. |

### Băi

| ID            | Decizie                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RM-BATH-01`  | Baia parterului deservește biroul, oaspeții și zona de zi și are duș walk-in la nivelul pardoselii, cu perete de sticlă, vas WC suspendat, lavoar pe mobilier cu sertar și dulap pentru prosoape.                                                                                                                                                                                                                                                                                                                                             |
| `RM-UBATH-01` | Baia etajului deservește dormitoarele și are cadă utilizabilă și ca duș, vas WC suspendat, lavoar pe mobilier și depozitare. Fiind singura baie cu cadă, se verifică cerința din Legea 114/1996, anexa nr. 1, ca suprafața băii să permită accesul la cadă al persoanelor imobilizate în scaun cu rotile; legea nu dă dimensiuni, iar arhitectul compară spațiul liber și lățimea ușii cu reperele NP 057-02 (1,50 × 1,50 m pentru manevra scaunului rulant, 0,80 m pentru ușile din interiorul locuinței) și stabilește modul de conformare. |

## La mutat

| ID            | Decizie                                                                                                                                                                                                                 |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RM-LIV-03`   | Livingul primește masa pentru șase persoane cu scaunele aferente și o măsuță joasă; canapeaua existentă se reutilizează conform [Bunurilor existente](existing-assets.md) (`AST-03`).                                   |
| `RM-MBED-02`  | Dormitorul matrimonial primește patul de 160 × 200 cm cu saltea nouă, două noptiere și lămpi de citit.                                                                                                                  |
| `RM-OFF-02`   | Biroul primește un birou reglabil pe înălțime, rafturi și canapeaua extensibilă pentru oaspeți; scaunul și biblioteca existente se reutilizează conform [Bunurilor existente](existing-assets.md) (`AST-04`, `AST-06`). |
| `RM-CHILD-02` | Camera copilului primește patul, salteaua, biroul, scaunul, dulapul și un covor potrivit jocului.                                                                                                                       |

## Extra

| ID            | Decizie                                                                                                                              |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `RM-CHILD-03` | Când copilul ajunge la vârsta gimnaziului, biroul și depozitarea camerei sale se adaptează pentru studiu, păstrând patul și dulapul. |
