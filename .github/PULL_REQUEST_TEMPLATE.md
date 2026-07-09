<!-- Dodajesz dataset? Wypełnij checklistę. Szczegóły: CONTRIBUTING.md -->

## Dataset
- **Nazwa:** <datasets/…>
- **Źródło (`source_url`):**
- **Licencja tekstu / kolekcji:**
- **Widoczność:** external | internal

## Checklista (bramka)
- [ ] `card.yaml` uzupełniony (name, version, license, visibility, source_url, sample)
- [ ] `visibility: external` → **otwarta licencja** (SPDX)
- [ ] `sample.jsonl` dołączony (próbka, **nie** surowe dane)
- [ ] rekordy mają unikalne `id` i niepuste `text`
- [ ] `dsbench audit --card datasets/<nazwa>/card.yaml` → **zielone lokalnie**
- [ ] brak PII (PESEL), duplikatów, nakładek z eval-setami
- [ ] (opcjonalnie) `sha256` pełnych danych w karcie

## Uwagi
<np. specyfika źródła, decyzje dot. preprocessing/licencji>
