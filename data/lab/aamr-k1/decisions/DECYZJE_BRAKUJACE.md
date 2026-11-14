# K1: stan decyzji właściciela (aktualizacja 2026-11-13, po odpowiedzi właściciela)

> **Stan aktualny (po zamrożeniu K1 v1.0): `RAPORT_GO_NOGO_K1.md`.** D1, D3, D4, D7, D8, D12 zatwierdzone; brakują D5 i D11 dla K1 oraz T1–T12.

Wartości i statusy są zapisane w `code/k1_config.json → decisions`.

**Nadzorca odmawia prawdziwego modelu (kod 3), dopóki którakolwiek decyzja nie ma statusu `approved…` albo `spec_frozen_sha256` jest pusty** (test U2).

| # | Decyzja | Stan | Co dalej |
|---|---|---|---|
| D1 | próg 10 pp | **przyjęta kierunkowo**. Warunek właściciela wpisany: stała „ZASADA INTERPRETACJI (D1)” w każdym raporcie; test U11 | ostateczne zatwierdzenie przy zamrożeniu |
| D2 | 0,7 / 0,8 / 20 | zatwierdzona w pilotażu; **pokrywa K1 dokładnie** | — |
| D3 | 3 kontrasty (M − P, M − X, M − S) | **przyjęta kierunkowo** | przy zamrożeniu |
| D4 | liczba bloków próbkowanych | **otwarta** | po jawnym raporcie pilotażu (`sampled_blocks`) |
| D5 | wykonawca i środowisko | zatwierdzona dla pilotażu; **nie pokrywa K1 w pełni**: runner koordynatora zamiast sesji, brak git (manifest L8) | potwierdzenie dla K1 |
| D6 | 148 zadań | zatwierdzona; **pokrywa K1 dokładnie**: bodźce identyczne z pilotażem (R4) | — |
| D7 | 98,33% | **przyjęta kierunkowo** | przy zamrożeniu |
| D8 | czy uruchamiać K1 | **otwarta** | po jawnym raporcie pilotażu |
| D9 | długość P (`c_d`, WR5, LEN) | przyjęta warunkowo, warunki wpisane | — |
| D10 | bramki budżetu | przyjęta | — |
| D11 | kontrole techniczne | zatwierdzona dla pilotażu (hak, `BfclK1`, L10); **K1 dodaje**: listy L4a, brak techniczny z checkera, odczyt tokenów z `responses.jsonl` NIGHT-2, `memory.items` z sesji NIGHT-2 (graf), wywołania T12 | potwierdzenie dla K1 |
| D12 | dopasowanie długości X/S | **przyjęta kierunkowo**; przewidywana nierównowaga X +1,84%, S +2,24% | przy zamrożeniu |
| T1–T12 | wybory techniczne | **niezatwierdzone**; dokładne znaczenie, wartości, ryzyka i dowody w `T1_T12_I_ZGODY.md`. Opcja T2b (dolna granica `m`) do rozstrzygnięcia | przy zamrożeniu |

Wariant „2 kontrasty” (D3) nie jest zaimplementowany, bo wymagałby zmiany zamrożonego kodu odczytu v0.4. Kierunkowa decyzja D3 = 3 kontrasty czyni go zbędnym.

Procedura startu i zatrzymania: `CHECKLISTA_STARTOWA_K1.md`.
