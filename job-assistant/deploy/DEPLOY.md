# Деплой бота 24/7 на Oracle Cloud (Always Free)

Бот работает на long-polling — ему нужен сервер, где процесс крутится постоянно.
Oracle Cloud даёт **бесплатный навсегда** VM (Always Free). Ниже — путь от нуля до
работающего бота. Ориентировочно 20–40 минут.

> Входящие порты боту не нужны (он сам ходит в Telegram), поэтому настраивать
> firewall/VCN не требуется — исходящий интернет на VM открыт по умолчанию.

---

## 1. Создать аккаунт и виртуальную машину

1. Зарегистрируйся на https://www.oracle.com/cloud/free/ (нужна банковская карта
   для верификации — деньги за Always Free не списываются).
2. В консоли: **Menu → Compute → Instances → Create instance**.
3. Параметры:
   - **Image**: Canonical Ubuntu 22.04 (или 24.04).
   - **Shape**: выбери Always Free eligible —
     `VM.Standard.A1.Flex` (ARM Ampere, 1 OCPU / 6 GB достаточно) либо
     `VM.Standard.E2.1.Micro` (AMD). Должна стоять пометка **Always Free**.
   - **SSH keys**: нажми «Generate a key pair for me» и **скачай приватный ключ**
     (или загрузи свой публичный ключ).
4. **Create**. Дождись статуса *Running* и скопируй **Public IP address**.

## 2. Подключиться по SSH

```bash
# путь к скачанному приватному ключу
chmod 600 ~/Downloads/ssh-key-*.key
ssh -i ~/Downloads/ssh-key-*.key ubuntu@<PUBLIC_IP>
```

(На Windows удобнее через PowerShell или PuTTY; пользователь по умолчанию — `ubuntu`.)

## 3. Установить и настроить бота

На сервере выполни по порядку:

```bash
# системные пакеты
sudo apt update && sudo apt install -y python3-venv python3-pip git

# код (нужная ветка с проектом)
git clone https://github.com/shapovalov-sv/telegram-sql-bot.git
cd telegram-sql-bot
git checkout claude/telegram-ai-agent-G2Gd9
cd job-assistant

# виртуальное окружение и зависимости
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# конфигурация — впиши свои токены
cp .env.example .env
nano .env      # BOT_TOKEN=...  и  ANTHROPIC_API_KEY=...  (Ctrl+O, Enter, Ctrl+X)
```

Проверь, что бот стартует вручную:

```bash
.venv/bin/python bot.py
# увидишь логи — значит, всё ок. Останови Ctrl+C и переходи к автозапуску.
```

## 4. Включить автозапуск 24/7 (systemd)

```bash
sudo cp deploy/job-assistant.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now job-assistant
```

Готово — бот работает и сам перезапускается при сбое или перезагрузке сервера.

## 5. Управление и логи

```bash
sudo systemctl status job-assistant     # состояние
journalctl -u job-assistant -f          # живые логи
sudo systemctl restart job-assistant    # перезапуск
sudo systemctl stop job-assistant       # остановить
```

## Обновление кода (когда что-то поменяется в репозитории)

```bash
cd ~/telegram-sql-bot && git pull
cd job-assistant && .venv/bin/pip install -r requirements.txt
sudo systemctl restart job-assistant
```

---

## Альтернатива: Docker (если предпочитаешь контейнеры)

На той же VM:

```bash
sudo apt install -y docker.io
sudo docker build -t job-assistant .
sudo docker run -d --name job-assistant --restart unless-stopped \
  --env-file .env -v job_assistant_data:/data job-assistant
```

Том `job_assistant_data` хранит SQLite-базу (профили, история, трекер), чтобы данные
переживали пересборку контейнера.

---

## Частые вопросы

- **Бот не отвечает.** Смотри `journalctl -u job-assistant -f`. Чаще всего — опечатка
  в `BOT_TOKEN`/`ANTHROPIC_API_KEY` или закончились средства на балансе Anthropic.
- **`ANTHROPIC_API_KEY не задан`.** Проверь, что `.env` лежит рядом с `bot.py` и пути
  в `job-assistant.service` совпадают с реальными.
- **Перезагрузил сервер — бот сам поднялся?** Да, благодаря `systemctl enable`.
