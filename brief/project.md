# Proiect

Acest fișier consemnează componența gospodăriei, parcela aleasă, limitele de buget și calendarul comun tuturor
disciplinelor. Proiectul demonstrativ se numește „Casa Exemplu” și este amplasat fictiv în Comuna Exemplu, județul
Exemplu, România.

| ID      | Decizie                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `HH-01` | Gospodăria este formată din doi adulți (Adultul A și Adultul B) și un copil de vârstă școlară, cu oaspeți ocazionali care rămân peste noapte. Adultul A lucrează de acasă în zilele lucrătoare, iar familia ia zilnic masa împreună și petrece serile în living și în grădină. Această componență este baza programului casei.                                                                                             |
| `HH-02` | Proiectul folosește o singură parcelă fictivă, dreptunghiulară, de circa 960 m², cu front la stradă, descrisă în [Arhitectură](architecture.md) (`SITE-01`). Nu are coordonate, număr cadastral sau orientare confirmată; datele reale se stabilesc prin ridicarea topografică și extrasul de carte funciară.                                                                                                              |
| `HH-03` | Bugetul se gestionează iterativ în aplicația de buget, cu un plafon demonstrativ stabilit în catalog; cifrele din catalog sunt exemple, nu prețuri de piață. În orice compromis de cost se protejează mai întâi performanța anvelopei, calitatea aerului și programul interior; se reduc întâi finisajele interschimbabile și amenajările exterioare care nu afectează accesul și siguranța. Prețul terenului este exclus. |
| `HH-04` | Calendarul orientativ prevede circa 12 luni pentru studii, proiectare și autorizare, circa 18 luni pentru execuție și mutarea familiei după recepția la terminarea lucrărilor; `Extra` acoperă circa doi ani după mutare. Lunile tranșelor din catalog sunt ipoteze de planificare, nu termene contractuale.                                                                                                               |
| `HH-05` | Ridicarea topografică, studiul geotehnic, certificatul de urbanism și validarea de către arhitect, inginerul structurist și proiectanții de instalații sunt condiții prealabile pentru orice geometrie definitivă. Conceptul din această temă și din model nu este o documentație de autorizare.                                                                                                                           |

## La roșu

Studiile, proiectarea și avizele necesare începerii lucrărilor sunt finalizate, iar autorizația de construire este
emisă conform Legii 50/1991 ([Referințe](references.md), `EV-04`); taxele aferente sunt achitate.

## La gri

Racordurile la utilități și traseele îngropate de pe parcelă se coordonează într-o singură campanie, conform
[Sistemelor](systems.md) (`EN-08`) și [Exteriorului](outdoor.md) (`GAR-06`).

## La cheie

Bugetul pentru predarea la cheie păstrează toate cerințele din fișierele tematice și folosește cantitățile curente din
catalog; calendarul plăților poate diferi de etapa la care o cerință este completă.

## La mutat

Catalogul separă dotările mobile și bunurile existente de lucrările fixe. Logistica mutării se planifică fără a
confunda data achiziției sau plății cu etapa de finalizare a cerinței.

## Extra

| ID      | Decizie                                                                                                                                                                                                                               |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `HH-06` | `Extra` are buget separat și nu intră implicit în suma rămasă de plată până la mutare. Infrastructura comună și finisajele constructive se realizează în etapele inițiale; în `Extra` rămân numai completările acceptate după mutare. |
