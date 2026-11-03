---
id: laravel
name: Laravel (PHP)
---

Notes from general knowledge, no versions pinned. Check the official docs for the version in `composer.json` before relying on a detail.

## Commands
- Run: composer run dev
- Test: php artisan test
- Lint / types: ./vendor/bin/pint --test
- Build: npm run build

## Start
- Check the current installation docs for PHP, Composer and Node requirements. New app: `laravel new <name>`, or `composer create-project laravel/laravel <name>`. Choose a starter kit only if the plan needs login screens.
- `composer run dev` exists in recent skeletons (server, queue, logs, Vite); read `composer.json` scripts, and fall back to `php artisan serve` plus `npm run dev`.
- Copy `.env.example` to `.env`, run `php artisan key:generate` if needed, set the database, `php artisan migrate`. SQLite is fine for development.

## Conventions
- Thin controllers. Validation in Form Request classes. Move logic to a service or action class only when a controller outgrows itself.
- Every schema change is a migration. Never edit a migration that has run anywhere shared; add a new one.
- Set `$fillable` explicitly on models. Eager load relations (`with`) to avoid N+1 queries. Use API Resources to shape JSON.
- Read `env()` only inside `config/*.php`; elsewhere use `config()` (`env()` breaks after `config:cache`).
- Blade `{{ }}` escapes output; avoid `{!! !!}` on anything a user can influence. Forms need `@csrf`.
- Follow the project's test framework (Pest or PHPUnit); do not mix them.

## Security
- Authorize every record access with Policies or Gates (`authorize`, `@can`), not just "is logged in".
- Production: `APP_DEBUG=false`, `APP_ENV=production`, `.env` never committed. Rate limit login and public APIs with `throttle` middleware.
- Uploads: validate type and size, store on a non-public disk unless they must be public.
- Run `composer audit` before release.

## Testing
- Feature tests call routes with `actingAs`, use `RefreshDatabase` and factories, and cover denied (403 or 404), invalid (422) and success paths.
- Fake external effects: `Http::fake()`, `Mail::fake()`, `Queue::fake()`, `Storage::fake()`.
- Browser tests (Pest browser plugin or Dusk) only for the critical flow.

## Release
- `php artisan migrate --force`, `php artisan optimize`, `npm run build`, `php artisan storage:link`, a queue worker under a process manager, correct storage permissions.
