# Uppgiftsbeskrivning – produktionsmiljö för ett API

Detta är en sammanställning av kursuppgiften som gruppen fick. [Projektplanen](project-plan.md#assignment-coverage-tracker) visar hur långt ServerWatch har kommit med varje krav.

## Uppdrag och team

Prototypa en enkel produktionsmiljö för kommande API-utveckling. Acceptera inbjudan till UA Classroom, skapa vid behov ett team om två och skriv i gruppdokumentationen vilka som hör ihop. Examinationen är individuell även om ni lämnar in samma video.

Ni får använda det medföljande API:t eller en egen applikation med minst motsvarande komplexitet. FastAPI och PostgreSQL ska ingå. En frontend är en tillåten utökning. Ni får använda AI för att generera kod och ska förstå och kunna förklara merparten av det ni visar.

## G – Godkänd

| Krav | Vad ni ska genomföra |
| --- | --- |
| G1 (AWS, EC2) | Skapa en ny EC2-instans med free-tier-inställningar **under inspelningen**. Välj lämplig AMI, konfigurera security groups och använd en Elastic IP. |
| G2 (SSH) | Sätt upp SSH-nycklar så att båda kan ansluta från varsin dator till samma instans. |
| G3 (Bash, SCP, Linux) | Skriv ett Bash-skript för grundkonfiguration med användbara alias och relevanta paket. Motivera eventuella extra användare och välj lämpliga behörigheter. Ni bör föra över skriptet med SCP och köra det på instansen. |
| G4 (Git, Linux) | Klona API-repositoryt till en användares hemkatalog och förklara hur ni valde att göra det. |
| G5 (Cron, backup) | Schemalägg säkerhetskopiering med Cron och spara kopior på EC2-instansen. Loggar och databasen är exempel i uppgiften. Ni kan dessutom kopiera hem filer med SCP. Tänk på att den lokala datorns IP kan ändras. |
| G6 (övervakning, avisering) | Schemalägg hälsokontroller och skicka aviseringar vid behov till Discord via webhook eller till e-post. Diskutrymme, CPU-belastning och avvikande SSH-beteende är exempel på vad ni kan övervaka. |
| G7 (systemd eller supervisor, HTTP) | Kör API:t via en processhanterare och visa att Swagger går att besöka på `http://<instansens-ip>/docs` eller motsvarande HTTPS-adress. |
| G8 (reverse proxy, Nginx) | Använd en reverse proxy. Nginx är förstahandsvalet och en annan lösning kräver en god motivering. |
| G9 (FastAPI, PostgreSQL) | Visa att det driftsatta API:t är anslutet till PostgreSQL. RDS behövs inte för G. |

Ni ska visa grundläggande teknisk förståelse och kunna förklara kommandona. Vid planeringen gäller de numrerade bedömningskraven ovan. Den inledande översikten nämner Nginx under VG, men punkt G8 kräver en reverse proxy redan för G.

## VG – Väl godkänd

Både VG1 och VG2 ska göras. Därutöver bedöms er tekniska förståelse och hur ni uppfyller övriga krav. Genomförda VG-steg garanterar inte betyget.

| Krav | Vad ni ska genomföra |
| --- | --- |
| VG1 (Docker, Compose, PostgreSQL) | Skapa en lämplig Dockerfile och Compose-fil och kör projektet i containrar på EC2 med PostgreSQL i en container. Ni kan utveckla och testa lokalt först. Visa också att ni kan driftsätta API:t via en processhanterare. Docker är huvudfokus för VG. |
| VG2 (DNS, HTTPS, Certbot) | Använd en egen domän och sätt upp HTTPS med certifikat från Certbot. |
| Bonus VG3 (AWS RDS) | Använd RDS som alternativ till lokal PostgreSQL. Vid detta alternativ behöver Compose inte skapa databasen. |
| Bonus VG4 (GitHub Actions, deployment) | Automatisera driftsättning av Docker-imagen till EC2. Konfigurera SSH-nycklar för GitHub. Ett eget repository är tillåtet om organisationens behörigheter hindrar Actions. Visa i så fall det egna repositoryt vid examinationen och skapa fortfarande ett team. |

## Inspelning och inlämning

- Spela in i par i **högst 60 minuter**. Gå igenom hela pipelinen från början, inklusive ny EC2-instans, SSH-nyckel, security groups och anslutning. Använd en annan instans för repetition.
- Båda ska synas och höras och terminaltexten ska gå att läsa. Arbeta parallellt eller åtminstone på varsin dator. Förklara kommandon och tekniska val under tiden så att bådas förståelse framgår.
- Repetera från en tom instans. Förbered gärna kod och en kort checklista för ordningen. Visa grundläggande terminalarbete för hand. Vid Nginx-konfiguration kan ni exempelvis navigera till katalogen, öppna filen i nano och sedan klistra in den förberedda konfigurationen.
- Kontrollera videolänken, ljudet, kamerorna och skärmens läsbarhet före inlämning. Information om hur ni lämnar in länken kommer i Discord och läroportalen.
- När inspelningen är kontrollerad ska ni stänga av instanserna. En öppen HTTP-port exponerar den körande instansen för internettrafik.
