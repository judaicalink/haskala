# Person data-quality audit

Four buckets surfaced from the live Person table before the Phase 1.5 Wikidata sweep. Curator decides per row.

## 1. Organization-like rows (5)

Likely NOT persons -- candidates to move to a separate model or mark as non-person before the sweep (Wikidata Q5 filter would skip them; an organisation QID like Q3918 would be wrong as a Person.wikidata_id).

| Name | Refs | Edit |
|---|---:|---|
| Gesellschaft des Guten und Edlen - חברת שוחרי הטוב והתושיה | 3 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/ae0dbba2-f86e-4017-a895-98c7c0037519/) |
| Israelitische Haupt- und Freischule zu Deßaus | 1 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/e11060dc-292c-45f9-951b-c4a14bfa759c/) |
| Gesellschaft der Freunde | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/51ce1013-1559-4e69-875f-f4b8a2fed12c/) |
| Gesellschaft der hebräischen Litteraturfreunde | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/503b4890-e4d3-495f-b226-f86bb44b994d/) |
| Wallenrodtsche Bibliothek | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/f61256f5-aba4-4818-a668-6580854783aa/) |

## 2. Titles in name (21)

`Freiherr`, `Graf`, `Baron`, `Edler von`, ` von `, `Ritter`, `Fürst`, `Herzog`, `Markgraf`, `Prinz` -- noise that hurts fuzzy name match. Curator can optionally normalize (move titles into pseudonym or a notes field) but it's not blocking for the sweep.

| Name | Refs | Edit |
|---|---:|---|
| Moses von Gottfried Jakob Schaller | 1 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/288d671a-f5ca-4d39-b282-e937615ee127/) |
| Arnstein (Freiherr von), Nathan Adam | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/1755766e-d7c8-427b-9008-396a875e75fb/) |
| Arnstein, Nathan Adam (Freiherr von Arnstein) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/4aae48ee-022f-4397-92e5-716006ba2719/) |
| Fürst (Dr.) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/92d0e837-36d9-43d7-b3be-5efc57aabe0a/) |
| Graff, Jacob | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/9c0fd0ae-5a80-40ec-9ad8-f90d5b5efee0/) |
| Hönig, Israel (Edler von Hönigsberg, k.k. Regierungsrath, Tabak- und Siegelgefäl | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/4c25e985-6344-46f7-a810-5ca092bd0577/) |
| Hönig, Joachim (Edler von Hönigsberg) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/e810c41a-9d92-4201-aaf3-cfbf279daf86/) |
| Hönig, Max (Edler von Hönig) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/37daafa8-8a94-43ab-a803-87d554669f8b/) |
| Hoym, Karl Heinrich Graf von (Graf, Minister) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/86d0fec1-915a-49f2-8bcd-76eec875cc4d/) |
| Hoym, Karl Heinrich Graf von (Graf, Minister) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/701666e2-8dd8-4cc2-a608-5f3106d16c64/) |
| Keyserling, Heinrich Christian (Reichsgraf) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/5aab6e82-e91b-4c52-8dcb-1d8ed7075eea/) |
| Kleist-Keyserling (Baron), Louis | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/67ad154d-6e43-470d-b846-7a84ff434fdf/) |
| Korff (Graf), von | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/9fc9c865-e0f4-4abd-aca8-c6fcd7d36290/) |
| Leopold Friedrrich Franz (Fürst) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/5166af32-210b-4d73-8789-94e067c8f4c2/) |
| Moses Fürst | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/563274b2-7344-425b-b497-d2d3e96f99ea/) |
| Stanislaus II. Poniatowski (König von Polen) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/96da76d0-4e04-41c3-bdd8-04fd6f0dde5a/) |
| Wertheimstein, Hermann von (Edler von) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/369a2eca-26bc-430f-af62-f31489b11d3b/) |
| Wertheimstein, Josef (Edler von Wertheimstein) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/295b65de-8ee6-48a5-8875-c8baa2cd5155/) |
| Wertheimstein, Lazar (Edler von Wertheimstein) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/3f51068c-34c2-4af9-8812-0f67388979f3/) |
| Wilhelm, Wertheimstein (Edler von Wertheimstein) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/10df07df-4a6c-4c9f-b621-7103f895c9d9/) |
| סאלאמאן, עדלער פאן הערץ (Edler von) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/4df02328-928b-439c-b2eb-22012972d9f6/) |

## 3. Parenthetical professions (39)

`(Pastor)`, `(Lehrer)`, `(Rabbi)`, etc. baked into the name. NOT the same as the system `Occupation` model (those are the Person-Buch role like Author / Editor). Curator can optionally strip + move to a profession note. Not blocking the sweep.

| Field | Name | Snippet | Refs | Edit |
|---|---|---|---:|---|
| pref_label | Adolphi (Pastor) | (Pastor) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/6d8bcee0-2c75-4c4b-bca1-b48a5d8c47f3/) |
| hebrew_name | בנעט, מרדכי (רב) | (רב) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/6fdd83b7-71e3-4973-8657-ec2e203427ec/) |
| pref_label | Cohn, Nathan (Lehrer) | (Lehrer) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/82b8e08b-291a-4ff6-a963-dfe85d9e6cdf/) |
| pref_label | Friedländer, H. N. (Buchhändler) | (Buchhändler) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/790f4e5f-98e8-4b5e-8579-66f20973428c/) |
| pref_label | Hartknoch (Buchhändler) | (Buchhändler) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/51bcf2dd-be2b-4900-8983-f090e32d0900/) |
| pref_label | Herz (Professor), Marcus | (Professor) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/e985de3b-e27d-4618-8689-ff291a542b33/) |
| pref_label | Hoym, Karl Heinrich Graf von (Graf, Minister) | (Graf, Minister) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/86d0fec1-915a-49f2-8bcd-76eec875cc4d/) |
| pref_label | Hoym, Karl Heinrich Graf von (Graf, Minister) | (Graf, Minister) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/701666e2-8dd8-4cc2-a608-5f3106d16c64/) |
| pref_label | Itzig (Oberkantor) | (Oberkantor) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/cccf3ea5-a152-42e9-88e4-7bddbb77e144/) |
| pref_label | Neumann, Israel Moses (Inspektor und Oberlehrer) | (Inspektor und Oberlehrer) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/ea12bbb7-59e1-4d0d-8ae3-71d389c0ff6b/) |
| pref_label | Wappler, Christian Friedrich (Buchhändler) | (Buchhändler) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/06f67f74-8b23-457b-a112-c5cd6ac7b2fa/) |
| pref_label | Weil, Abraham (Oberrabbiner) | (Oberrabbiner) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/a0b08ac0-76bc-41b2-a889-dc386eb7b0b3/) |
| hebrew_name | אביגדור ברעסלוי (רב) | (רב) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/7decefac-1fd7-4125-90e9-e76c1609b755/) |
| hebrew_name | בומבורג (רב), אברהם | (רב) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/662395e3-4947-4ecc-ab7d-746d18c53298/) |
| hebrew_name | אהרן בן יוסף אהרן הלוי הורוויץ (רב ודיין (הסכמת רבני יושבי ע | (רב ודיין (הסכמת רבני יושבי על | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/75f07217-41a0-4c00-bcfd-d713c2d89b56/) |
| hebrew_name | אהרן ב"ר משה מגזע צבי ראב"ד בק"ק ברלין (רב) | (רב) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/6707c650-14f0-45b1-af1c-ea57a51395ea/) |
| hebrew_name | אלעזר קאליר (רב) | (רב) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/727ed808-a8d2-454b-957d-a01521722564/) |
| hebrew_name | קאליר (רב), אלעזר | (רב) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/c7be9e4c-007d-49a1-8161-de5919ea636d/) |
| hebrew_name | בנעט, מרדכי (רב מדינת מעהרין) | (רב מדינת מעהרין) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/7844712e-db6d-4dda-ad21-33dd94867137/) |
| hebrew_name | זנוויל נייאגאס (רב ודיין (הסכמת רבני יושבי על מדין)) | (רב ודיין (הסכמת רבני יושבי על | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/63b91fe8-a135-4da5-8fa8-865e0b5cbab5/) |
| hebrew_name | חיים מצאנז (המקובל האלהי הרב) | (המקובל האלהי הרב) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/3bc5f452-aba2-485c-981b-b529c802b935/) |
| hebrew_name | יואל במהר"ר יקותיאל מגלוגא (רב, דיין) | (רב, דיין) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/6add4cce-d0d9-4b68-b256-87f54dae5649/) |
| hebrew_name | יוסף משטיין הרט (רב) | (רב) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/5437d6b4-f569-469e-b061-7139288f26b8/) |
| hebrew_name | לנדא (רב), יחזקאל הלוי | (רב) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/e687370b-fe4a-4c9a-9b98-92c58c61a917/) |
| hebrew_name | עמדן (רב), יעקב | (רב) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/b55593a6-d97b-4d8d-a424-29ab9ed36326/) |
| hebrew_name | יצחק הלוי מלבוב (רב) | (רב) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/0a46350d-fbac-471c-b941-e2ec0833ab04/) |
| hebrew_name | מיכאל בלא"א המנוח מו"ה זנוויל בכרך (רב) | (רב) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/aa607f4b-3125-4a29-9912-f4e626ba5585/) |
| hebrew_name | מרדכי (רב, אב"ד) | (רב, אב"ד) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/d4aca39b-e8cd-4fea-b3e9-a4c5724399f2/) |
| hebrew_name | נפתלי הירש ב"ר משה לבית קצנאלנבוגן (רב) | (רב) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/7526fd09-4749-4251-827b-1da78c702ebf/) |
| hebrew_name | נתנאל אשכנזי ווייל מפראג (רב) | (רב) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/cc101654-bdbf-4218-be43-b5c2dcaa935b/) |
| hebrew_name | הירש (רב, אב"ד), צבי | (רב, אב"ד) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/54b8cdb0-6db8-410b-b189-5a679baf8e1a/) |
| hebrew_name | צבי הירש (רב, אב"ד) | (רב, אב"ד) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/76a32602-726f-4c3a-8eae-806e52a903fe/) |
| hebrew_name | צבי הירש (רב, אב"ד) | (רב, אב"ד) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/89ea11af-77fe-44ca-af53-cbc554df81c5/) |
| hebrew_name | צבי הירש (רב, אב"ד) | (רב, אב"ד) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/7916da3a-903b-4bc1-98f3-ef7b9e72c7be/) |
| hebrew_name | הירש (רב, אב"ד), צבי | (רב, אב"ד) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/08cd28f3-d636-4689-94ed-681cc77a25f1/) |
| hebrew_name | צבי הירש ליבשיץ (סופר ונאמן) | (סופר ונאמן) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/16755649-1a11-4d4b-a668-5a0a09dfdb08/) |
| pref_label | צבי הירש ראזאנים (הרב אב"ד דק"ק לבוב וקרייז) | (הרב אב"ד דק"ק לבוב וקרייז) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/68e051ee-fc52-4fcb-88a5-bc972ca57920/) |
| hebrew_name | שלמה מבראד (רב דק"ק טורהאוויץ) | (רב דק"ק טורהאוויץ) | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/9e2668a2-9514-4770-978c-b1a14416b93b/) |
| hebrew_name | שמואל זנוויל בראנדיבורג (רב ודיין [הסכמת רבני יושבי על מדין] | (רב ודיין [הסכמת רבני יושבי על | 0 | [edit](https://www.haskala-library.net/dashboard/snippets/home/person/edit/e91fcf74-bf8c-4219-ae66-3b9abf81a853/) |

## 4. Duplicates

Already covered by `docs/audits/person_duplicates.csv` (203 keys across 510 rows). Curator merges via Wagtail admin where appropriate -- but proceed carefully because same-name persons may legitimately be different (father/son, namesakes etc.).
