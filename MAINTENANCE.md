# Plan de maintenance — django-session-security

> Repo : https://github.com/yourlabs/django-session-security
> Date du plan : 2026-04-20 (vérifié sur code réel)
> Criticité : **HAUTE** — middleware de sécurité, 312 stars, 138 forks, 31 issues ouvertes

---

## État actuel (vérifié sur le code source)

### Versions déclarées vs réalité

| Axe | Fichier | Valeur constatée | État |
|---|---|---|---|
| Version PyPI | `setup.py:46` | `2.6.7` | Pas de release depuis 2024-07-10 |
| Python classifiers | `setup.py:80-84` | 3.8, 3.9, 3.10 **seulement** (3.11 absent des classifiers, présent CI) | Incomplet |
| Django classifiers | `setup.py:65-75` | 1.8 → 4.1 (5.x absent) | Obsolète |
| CI Python matrix | `.github/workflows/tests.yml:13` | `['3.8', '3.9', '3.10', '3.11']` | 3.8 EOL, 3.12/3.13 absents |
| CI runner | `.github/workflows/tests.yml:9` | `ubuntu-22.04` | Vieillissant |
| CI actions | `.github/workflows/tests.yml:16-19` | `actions/checkout@v1`, `actions/setup-python@v2` | Très obsolètes |
| tox envlist | `tox.ini:2-6` | py27→py311, django18→41 ; **aucun django50/51/52** | Django 5.x absent |
| tox selenium | `tox.ini:14` | `selenium<4.3.0` | Bloque Selenium 4.x |
| `six` dans le code métier | `session_security/*.py` | **Aucune occurrence** — déjà absent | PR #159 partiellement superflue |
| `six` dans docs | `docs/source/conf.py:15,47` | `import six` + `six.u(html)` | Reste dans docs uniquement |
| `db.sqlite` dans test_project | `test_project/db.sqlite` | **Fichier présent** | Non exclu du dépôt |
| `.gitignore` | `.gitignore:9` | Contient `db.sqlite` (sans chemin) | Règle insuffisante — ne couvre pas `test_project/db.sqlite` |

---

## Phase 1 — Actions immédiates (release 2.6.8)

La communauté attend une release depuis plus de 2 ans (issue #164).

### 1.1 PRs à merger

**PR #159 — `remove six usage`** — **Fait.** `import six` et `six.u(html)` retirés de `docs/source/conf.py`.

**PR #160 — Snyk : `sqlparse` 0.4.4 → 0.5.0 (CVSS 7.5)** — **Fait.** `sqlparse>=0.5.0` ajouté à `docs/requirements.txt`.

**PR #161 — Snyk : `zipp` 3.15.0 → 3.19.1** — **Fait.** `zipp>=3.19.1` ajouté à `docs/requirements.txt`.

**PR #165 — `super(..) -> super()`** — **Fait.** 4 appels old-style modernisés (test_base.py:30, test_base.py:59, test_middleware.py:16, urls.py:23). Note : test_base.py:44 (`super(LiveServerTestCase, self)`) est intentionnel — il saute délibérément StaticLiveServerTestCase.setUp() dans le MRO.

### 1.2 Actions release 2.6.8

- [x] Bumper `setup.py:46` : `version='2.6.7'` → `version='2.6.8'`
- [x] Mettre à jour `CHANGELOG`
- [ ] Créer le tag Git `2.6.8` et publier sur PyPI
- [ ] Fermer l'issue #164 après publication

---

## Phase 2 — Bugs à corriger

### 2.1 Bug #46 — `ValueError: time data does not match format` (CORRIGÉ)

**Localisation exacte :** `session_security/utils.py:17-18`

```python
# utils.py:17-18 — problème
return datetime.strptime(session['_session_security'],
        '%Y-%m-%dT%H:%M:%S.%f')
```

`set_last_activity` écrit toujours avec `.%f` (`utils.py:8`), mais des sessions créées par d'anciennes versions (ou via des backends qui sérialisent différemment) peuvent stocker sans microsecondes. Le `except` actuel ne capture que `AttributeError` et `TypeError` — une `ValueError` (format mismatch) n'est **pas capturée** et lèvera une exception 500.

**Fix précis :**

```python
# utils.py:16-38 — remplacer la fonction get_last_activity
def get_last_activity(session):
    try:
        return datetime.strptime(session['_session_security'],
                '%Y-%m-%dT%H:%M:%S.%f')
    except ValueError:
        try:
            return datetime.strptime(session['_session_security'],
                    '%Y-%m-%dT%H:%M:%S')
        except (ValueError, TypeError):
            return datetime.now()
    except (AttributeError, TypeError):
        return datetime.now()
```

### 2.2 Bug #114 — `NoReverseMatch: session_security_ping not found` (CORRIGÉ)

**Localisation exacte :** `session_security/middleware.py:71`

```python
# middleware.py:71 — appel non protégé
elif (request.path == reverse('session_security_ping') and
```

Si les URLs `session_security` ne sont pas incluses dans `urlpatterns`, `reverse('session_security_ping')` lève `NoReverseMatch` à **chaque requête authentifiée**, provoquant une erreur 500.

**Fix précis :** Entourer d'un try/except dans `process_request` :

```python
from django.urls import reverse, resolve, Resolver404, NoReverseMatch

# middleware.py:71 — remplacer
try:
    ping_url = reverse('session_security_ping')
except NoReverseMatch:
    ping_url = None

if ping_url and request.path == ping_url and 'idleFor' in request.GET:
    self.update_last_activity(request, now)
elif not self.is_passive_request(request):
    set_last_activity(request.session, now)
```

Note : le commentaire `# TODO: check namespaces too` à `middleware.py:44` confirme que la gestion des namespaces (issue #96) est un problème connu non traité.

### 2.3 Bug #133 / Django 5.x — Logout POST obligatoire (CORRIGÉ)

**Localisation exacte :** `session_security/templates/session_security/all.html:34`

```html
returnToUrl: {% url 'logout' %},
```

Le JS (`script.js:60`) fait un simple `window.location.href = this.returnToUrl` — soit une redirection GET vers l'URL de logout. Depuis Django 5.x, `django.contrib.auth.views.LogoutView` **n'accepte plus GET** (renvoie 405). Le rechargement silencieux après expiration ne déconnecte donc plus l'utilisateur sur Django 5.x.

**Impact :** L'utilisateur voit la page rechargée mais reste authentifié côté serveur si `SESSION_SECURITY_REDIRECT_TO_LOGOUT=True`.

**Fix requis :**
- Soit modifier `script.js:expire()` pour soumettre un formulaire POST avec token CSRF vers `{% url 'logout' %}`.
- Soit ajouter un setting `SESSION_SECURITY_LOGOUT_METHOD = 'GET'|'POST'` (défaut `'POST'` pour Django 5+).
- La template `all.html` doit injecter le CSRF token dans le JS si POST est utilisé.

### 2.4 Race condition #1 — Session timeout prématuré (CONFIRMÉ, architectural)

**Localisation exacte :** `session_security/middleware.py:57-75` (`process_request`) + `session_security/views.py:28` (`PingView.get`)

Le problème : `process_request` lit `now = datetime.now()` au début de la requête (`middleware.py:58`), mais une requête longue (ex. `test_project/urls.py` contient une `SleepView`) va écraser `_session_security` avec un timestamp périmé **au moment de la réponse**, alors qu'une activité plus récente a peut-être été enregistrée entre-temps.

**Workaround documentable :** Ne pas écraser `_session_security` si la valeur en session est déjà plus récente que `now` au moment de l'écriture. La logique `update_last_activity` (`middleware.py:77-101`) fait déjà cette comparaison pour les pings, mais `process_request:75` (`set_last_activity(request.session, now)`) ne le fait pas pour les requêtes normales.

### 2.5 Issue #34 — `nextPing` implicite dans script.js (CORRIGÉ)

**Localisation exacte :** `session_security/static/session_security/script.js:145,151`

```javascript
// script.js:145 — variable globale implicite (pas de var/let/const)
nextPing = this.expireAfter - idleFor;
// script.js:151
nextPing = this.warnAfter - idleFor;
```

`nextPing` est déclarée sans `var`/`let`/`const` — elle devient une variable globale implicite. En mode strict (`'use strict'`) cela lèverait un `ReferenceError`.

**Fix :** Ajouter `let nextPing;` au début de la méthode `apply()` (ligne ~133).

---

## Phase 3 — Modernisation

### 3.1 Matrice tox — mise à jour (`tox.ini`)

```ini
envlist =
    py{310,311}-django{42,50,51,52}
    py312-django{42,50,51,52,60}
    py313-django{51,52,60}
    py314-django60
```

17 environnements couvrant toutes les combinaisons valides (Django 6.0 ne supporte pas Python < 3.12 ; Django 4.2/5.0 ne supportent pas Python 3.13+). **Fait.**

### 3.2 CI GitHub Actions — mise à jour (`.github/workflows/tests.yml`)

- `runs-on: ubuntu-latest`
- `actions/checkout@v4`
- `actions/setup-python@v5`
- matrix : `['3.10', '3.11', '3.12', '3.13', '3.14']`

**Fait.**

### 3.3 setup.py — classifiers (`setup.py:61-86`)

À ajouter :
- `'Framework :: Django :: 4.2'`
- `'Framework :: Django :: 5.0'`, `'5.1'`, `'5.2'`
- `'Programming Language :: Python :: 3.11'`
- `'Programming Language :: Python :: 3.12'`
- `'Programming Language :: Python :: 3.13'`

À retirer :
- `'Framework :: Django :: 1.8'` jusqu'à `'Framework :: Django :: 1.11'`
- `'Framework :: Django :: 2'`, `'Framework :: Django :: 2.2'`
- `'Programming Language :: Python :: 3.8'`

### 3.4 is_authenticated — dead code (`middleware.py:103-111`) (CORRIGÉ)

```python
# middleware.py:106-108 — branche Django < 1.10 morte
if django.VERSION < (1, 10):
    is_authenticated = request.user.is_authenticated()  # callable, Django < 1.10
else:
    is_authenticated = request.user.is_authenticated    # propriété, Django >= 1.10
```

Django 1.10 est EOL depuis 2017 et le projet a déjà retiré le support Django <3.2 (`tox.ini`). Cette branche ne sera jamais exécutée. **Supprimer les lignes 106-108**, garder uniquement `return request.user.is_authenticated`.

### 3.5 Packaging

- [ ] Migrer `setup.py` → `pyproject.toml` (PEP 517/518)
- [ ] `test_project/db.sqlite` : présent dans le dépôt (confirmé). Le `.gitignore:9` contient `db.sqlite` mais la règle ne matche que la racine. Ajouter `**/db.sqlite` ou `test_project/db.sqlite`.
- [ ] Mettre à jour Selenium : `tox.ini:14` `selenium<4.3.0` → `selenium>=4.0` (issue #148)

---

## Phase 4 — Documentation

- [ ] `docs/source/conf.py:15,47` : remplacer `import six` / `six.u(html)` par `html.encode('utf-8')` (objet de PR #159 pour les docs)
- [ ] Documenter `SESSION_SECURITY_REDIRECT_TO_LOGOUT` et ses implications Django 5.x (voir bug 2.3)
- [ ] Issue #95 : le setting s'appelle `SESSION_SECURITY_REDIRECT_TO_LOGOUT` (confirmé dans `session_security/templatetags/session_security_tags.py:21`), pas `NO_RELOAD`. Documenter avec avertissement sécurité.
- [ ] Issue #96/#114 : documenter l'inclusion des URLs avec namespace et le TODO visible à `middleware.py:44`
- [ ] Merger PR #127 et #123 (clarifications `quick.rst`, ouvertes depuis 2019)
- [ ] Issue #134 : mettre à jour la doc Quick Setup (settings dépréciés)

---

## Phase 5 — Issues à fermer comme obsolètes

- [ ] **#97** — `is_authenticated()` callable : corrigé à `middleware.py:109`. **Fermer comme résolu.**
- [ ] **#100** — Django 1.7 : hors scope depuis la suppression Django <3.2. **Fermer.**
- [ ] **#41** — RequireJS : obsolète. **Fermer wontfix.**
- [ ] **#34** — `nextPing` implicite : **non corrigé** (voir bug 2.5 ci-dessus). **Ne pas fermer — corriger d'abord.**
- [ ] **#9** — Redirect after login : hors scope. **Fermer wontfix** avec référence au paramètre `next` de Django.
- [ ] **#15** — Countdown timer : `script.js` contient déjà `startCounter()`/`stopCounter()` et `counterElementID`. **Vérifier si c'est suffisant avant de fermer.**

---

## Résumé des actions par ordre de priorité

### Urgence absolue (dans les 2 semaines)

- [x] Merger PR #160 (sqlparse CVSS 7.5 — docs)
- [x] Merger PR #161 (zipp — docs)
- [x] Merger PR #159 (six — `docs/source/conf.py` uniquement)
- [x] Merger PR #165 (super() — tests uniquement)
- [x] Bumper `setup.py:46` → `2.6.8`, mettre à jour CHANGELOG
- [ ] Créer le tag Git `2.6.8` et publier sur PyPI
- [ ] Fermer issue #164

### Court terme (1 mois)

- [x] Corriger bug #46 (`ValueError`) dans `session_security/utils.py`
- [x] Corriger bug #114 (`NoReverseMatch`) dans `session_security/middleware.py`
- [x] Corriger bug #34 (`nextPing` global) dans `session_security/static/session_security/script.js`
- [x] Supprimer dead code `middleware.py` (branche Django < 1.10, imports Django < 2.0)
- [x] Ajouter `**/db.sqlite` au `.gitignore`
- [ ] Retirer `test_project/db.sqlite` du dépôt (git rm)
- [ ] Fermer issues obsolètes #97, #100 avec message explicatif

### Moyen terme (2–3 mois)

- [x] Mettre à jour `tox.ini` : matrice py{310-314}×dj{42,50,51,52,60} (17 envs)
- [x] Mettre à jour CI : Python 3.10–3.14, `ubuntu-latest`, `checkout@v4`, `setup-python@v5`
- [x] Corriger bug Django 5.x logout POST (`all.html` + `script.js:expire()`)
- [x] Mettre à jour `setup.py` classifiers (retirer Django 1.x/2.x/3.x, ajouter 4.2/5.x/6.x)
- [ ] Merger PR #127, #123 (docs `quick.rst`)
- [ ] Fermer issues obsolètes #41, #9

### Long terme (3–6 mois)

- [ ] Migrer `setup.py` → `pyproject.toml`
- [ ] Mettre à jour Selenium (`tox.ini:14` : `selenium<4.3.0` → `selenium>=4.0`)
- [ ] Documenter et corriger race condition issue #1 (`middleware.py:75` vs `update_last_activity`)
- [ ] Publier release `2.7.0` avec Django 5.2 LTS et Python 3.13
- [ ] Vérifier si `startCounter()`/`stopCounter()` dans `script.js` répond à l'issue #15 (countdown timer)
- [ ] Évaluer feature requests #110, #104, #129

---

*Plan mis à jour le 2026-04-20 — chaque point vérifié sur le code source local du repo.*
