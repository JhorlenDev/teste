# Catalogo de Cursos Fametro

Aplicacao Flask para exibir cursos de graduacao e tecnicos em uma vitrine institucional, com painel administrativo para cadastro, edicao e exclusao.

## Como executar

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

Abra `http://127.0.0.1:5000`.

## Acesso do admin

- URL: `http://127.0.0.1:5000/admin/login`
- Senha padrao: `fametro123`

Voce pode trocar a senha definindo a variavel `ADMIN_PASSWORD`.
