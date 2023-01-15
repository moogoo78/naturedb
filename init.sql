
INSERT INTO "collection" ("created", "updated", "id", "name", "label", "organization_id") VALUES
(NULL,	NULL,	1,	'HAST main',	'HAST',	1);

INSERT INTO "organization" ("created", "updated", "id", "name", "short_name", "code") VALUES
(NULL,	NULL,	1,	'中研院植物標本館',	'BRMAS HAST',	'HAST');


INSERT INTO "assertion_type" ("created", "updated", "id", "name", "label", "target", "sort", "data", "collection_id", "input_type") VALUES
(NULL,	NULL,	1,	'veget',	'植群型',	'entity',	1,	NULL,	1,	'select'),
(NULL,	NULL,	6,	'humidity',	'環境溼度',	'entity',	6,	NULL,	1,	'select'),
(NULL,	NULL,	3,	'topography',	'地形位置',	'entity',	2,	NULL,	1,	'select'),
(NULL,	NULL,	4,	'naturalness',	'自然度',	'entity',	4,	NULL,	1,	'select'),
(NULL,	NULL,	2,	'habitat',	'微生育地 (微棲地?)',	'entity',	3,	NULL,	1,	'select'),
(NULL,	NULL,	5,	'light-intensity',	'環境光度',	'entity',	5,	NULL,	1,	'select'),
(NULL,	NULL,	7,	'abundance',	'豐富度 ',	'entity',	7,	NULL,	1,	'select'),
(NULL,	NULL,	8,	'life-form',	'生長型',	'unit',	1,	NULL,	1,	'select'),
(NULL,	NULL,	10,	'flower',	'花期',	'unit',	3,	NULL,	1,	'select'),
(NULL,	NULL,	11,	'flower-color',	'花色',	'unit',	4,	NULL,	1,	'select'),
(NULL,	NULL,	12,	'fruit',	'果期',	'unit',	5,	NULL,	1,	'select'),
(NULL,	NULL,	13,	'fruit-color',	'果色',	'unit',	6,	NULL,	1,	'select'),
(NULL,	'2022-12-20 14:43:38.359661',	9,	'plant-h',	'植株高度',	'unit',	2,	NULL,	1,	'input'),
(NULL,	'2022-12-21 11:17:28.112211',	14,	'sex-char',	'性狀描述',	'unit',	8,	NULL,	1,	'text'),
(NULL,	'2022-12-21 11:17:34.0655',	15,	'add-char',	'備註1',	'unit',	12,	NULL,	1,	'text'),
(NULL,	'2022-12-21 11:17:40.814903',	16,	'name-comment',	'命名備註?',	'unit',	16,	NULL,	1,	'text'),
(NULL,	'2022-12-31 06:06:42.569901',	17,	'is-greenhouse',	'溫室 ',	'unit',	16,	NULL,	1,	'input'),
('2022-12-27 15:06:58.150669',	'2023-01-03 11:42:49.629617',	18,	'algae',	'標本類型2x',	'entity',	1,	NULL,	2,	'input'),
('2023-01-03 11:50:29.149335',	'2023-01-03 11:50:29.14939',	20,	'abb',	'cdd',	'unit',	0,	NULL,	3,	'input'),
('2023-01-03 11:48:52.128037',	'2023-01-03 11:52:02.764911',	19,	'foo1',	'bar1',	'entity',	0,	NULL,	2,	'input'),
('2023-01-03 11:53:15.639489',	'2023-01-03 11:53:15.639505',	22,	'ue',	'aoeu',	'entity',	0,	NULL,	2,	'input'),
('2023-01-03 11:54:04.249154',	'2023-01-03 11:54:04.249171',	23,	'aaa',	'uuu',	'entity',	0,	NULL,	3,	'input'),
('2023-01-03 11:54:39.521552',	'2023-01-03 11:54:39.521618',	24,	'nnn',	'ppp',	'entity',	0,	NULL,	NULL,	'');


INSERT INTO "article_category" ("id", "name", "label", "organization_id") VALUES
(1,	'hast',	'本館消息',	NULL),
(2,	'digital-archive',	'數位典藏',	NULL),
(3,	'seminar',	'學術',	NULL),
(4,	'plant-news',	'植物快訊',	NULL),
(5,	'activity-exhibition',	'活動與展覽',	NULL),
(6,	'system-notice',	'系統公告',	NULL);
