# AGENTS.md

This file contains information for AI assistants working with the djangocms-versioning codebase.


Use ast-grep and gh cli tools freely.

## Project Overview

django CMS Versioning is a Django package that provides versioning capabilities for django CMS 4.0+. It's a hybrid Python/JavaScript project with a Django backend and frontend assets built with webpack and gulp.

## Frequently Used Commands

### Testing
```bash
# Install test dependencies
pip install -r tests/requirements.txt

# Run all tests
python setup.py test

# Run tests with coverage
coverage erase
coverage run setup.py test
coverage report

# Run tests with tox (multiple Python/Django versions)
tox

# Run specific tox environment
tox -e py311-dj42-sqlite
```

### Linting and Code Quality
```bash
# Run ruff linter (this is the primary linter)
ruff djangocms_versioning
ruff tests

# Run ruff with auto-fix
ruff --fix djangocms_versioning tests

# Run pre-commit hooks (automatically runs on commit)
pre-commit run --all-files

# Run ESLint for JavaScript
npm run lint  # or gulp lint
```

### Frontend Development
```bash
# Install JavaScript dependencies
npm install

# Build frontend assets
npm run build  # or use gulp/webpack directly
```

### Database Migrations
```bash
# Run migrations
python manage.py migrate djangocms_versioning

# Create versions for existing database (only for migration from non-versioned setup)
python manage.py create_versions --userid <user-id>

# Compile translations
python manage.py compilemessages
```

### Documentation
```bash
# Generate HTML documentation
cd docs/
make html
# Output will be in docs/_build/html/
```

### Translations
```bash
# Update translations from Transifex (requires transifex CLI)
tx pull

# Compile message files
python manage.py compilemessages
```

## Code Style and Conventions

### Python
- **Linter**: ruff (configured in pyproject.toml)
- **Line length**: 120 characters
- **Import style**: Use `isort` via ruff (combine-as-imports = true)
- **Code quality**: Follows ruff rules including pycodestyle, pyflakes, flake8-bugbear, and pyupgrade
- **Type hints**: Prefer modern Python type annotations
- **Django version**: Support Django 4.2, 5.0, 5.1, 5.2
- **Python version**: Python 3.9+

### JavaScript
- **Linter**: ESLint (configured in .eslintrc.js)
- **Bundler**: webpack 3.x
- **Task runner**: gulp
- **Transpiler**: Babel with env preset
- **Dependencies**: jQuery, lodash (debounce, memoize), nprogress

### General
- Use pre-commit hooks for automatic code quality checks
- Follow existing patterns in the codebase
- Migrations go in `djangocms_versioning/migrations/`
- Templates go in `djangocms_versioning/templates/`
- Static files go in `djangocms_versioning/static/`

## Project Structure

```
djangocms-versioning/
├── djangocms_versioning/     # Main package
│   ├── admin.py              # Django admin configuration
│   ├── models.py             # Database models
│   ├── forms.py              # Django forms
│   ├── managers.py           # Custom model managers
│   ├── signals.py            # Django signals
│   ├── handlers.py           # Signal handlers
│   ├── versionables.py       # Versionable configuration
│   ├── cms_config.py         # CMS app configuration
│   ├── cms_toolbars.py       # Toolbar customization
│   ├── management/           # Management commands
│   ├── templates/            # Django templates
│   ├── static/               # CSS, JS, images
│   ├── locale/               # Translations
│   ├── test_utils/           # Test utilities and example app (polls)
│   └── migrations/           # Database migrations
├── tests/                    # Test suite
│   └── requirements/         # Test dependency specifications
├── docs/                     # Documentation (Sphinx)
├── pyproject.toml            # Python package configuration
├── setup.py                  # Legacy setup file
├── test_settings.py          # Django settings for tests
├── tox.ini                   # Tox configuration
├── package.json              # JavaScript dependencies
├── webpack.config.js         # Webpack configuration
├── gulpfile.js               # Gulp tasks
└── .pre-commit-config.yaml   # Pre-commit hooks
```

## Key Dependencies

### Python
- Django >= 4.2
- django-cms >= 4.1.1
- django-fsm < 3
- packaging

### JavaScript
- jquery ^3.3.1
- webpack ^3.0.0
- babel ^6.x
- gulp 3.9.1

## Testing Strategy

- Tests are in the `tests/` directory
- Use Django's test framework
- Test against multiple Python versions (3.9, 3.10, 3.11)
- Test against multiple Django versions (4.2, 5.0, 5.1, 5.2)
- Example implementation in `djangocms_versioning/test_utils/polls/`
- Coverage configured to omit migrations, test utils, and tests themselves

## Integration Notes

- Versioning integration docs: `docs/versioning_integration.rst`
- Example implementation: `djangocms_versioning/test_utils/polls/cms_config.py`
- Requires django CMS 4.0 or higher
- Uses django-fsm for state machine functionality
- Frontend integrates with django CMS toolbar system

## Common Patterns

- **Versionable models**: See `test_utils/polls/models.py` and `test_utils/polls/cms_config.py`
- **Admin customization**: Versioning-specific admin in `admin.py`
- **State management**: Uses django-fsm for version states
- **Signals**: Version lifecycle signals in `signals.py`
- **Templates**: Override in `templates/djangocms_versioning/`
