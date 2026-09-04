# Master CRM Production

Готовый проект CRM для мастера: мобильный интерфейс, календарь выездов на главном экране, дата и время выезда, статусы, цена, комментарий и общая работа для двух мастеров.

## В проекте уже есть

- mobile-first интерфейс под смартфоны;
- календарь месяца на главном экране;
- заявки автоматически попадают в день выезда в календаре;
- список заявок на выбранную дату;
- фильтры по статусу, мастеру и поиску;
- SQLite база;
- FastAPI backend;
- systemd unit для запуска;
- nginx конфиг для доступа по IP сервера.

## Структура

- `app.py` — приложение и интерфейс;
- `requirements.txt` — Python зависимости;
- `master-crm.service` — unit для systemd;
- `nginx-master-crm.conf` — конфиг nginx;
- `data/` — каталог базы SQLite.

## Демо-доступ

- `master1 / 1111`
- `master2 / 2222`

После запуска лучше сразу поменять пароли прямо в `app.py`.

## Что нужно сделать на сервере позже

1. Скопировать проект в `/opt/master-crm`.
2. Создать venv и поставить зависимости.
3. Положить unit в `/etc/systemd/system/`.
4. Положить nginx-конфиг в `/etc/nginx/sites-available/` и включить его.
5. Запустить сервис и проверить `http://IP_СЕРВЕРА`.

## Мини-план деплоя

```bash
cd /opt/master-crm
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Потом:

```bash
cp master-crm.service /etc/systemd/system/master-crm.service
systemctl daemon-reload
systemctl enable --now master-crm
systemctl status master-crm
```

И nginx:

```bash
cp nginx-master-crm.conf /etc/nginx/sites-available/master-crm
ln -sf /etc/nginx/sites-available/master-crm /etc/nginx/sites-enabled/master-crm
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
```

## Бэкап базы

```bash
cp data/crm.db data/crm.db.backup-$(date +%F-%H%M)
```
