# Fixes
- [X] Allauth now does not set username to login from before @, resulting in blank name https://chatgpt.com/c/694428e2-c238-832c-8a6f-233adc497be3
- [ ] W zgłoszeniach jest dostepna ikona wyników
- [X] Does copying a contest maintain it's creator, or current user is set (same for dates)?
- [X] How does copying a contest maintain categories/styles? - Creates a copy of category linking to the same style
## Multicompetition
- [ ] Results
- [ ] Admin panel - participants
# Refactoring
- [ ] Use ContestContextMixin where contest context is required (or rather use middleware?)
- [ ] Co się stanie z danymi jak zostanie usunięte konto użytkownika?
- [ ] Cleanup requirements
- [X] Modify Style-Category-Contest - maybe Category should feature it's own name, not necesarly a copy fo the style?
- No, this would imply necesity to create name and translated name.we already have a feature on style level to prevent further use in contests.
- [ ] User roles refactor - users need to have role(s) in the context of contest. Ensure each role can act only if contest is in particular status
- [ ] Role-Capability-Predicate policy roles maping
- [ ] Docs are tracked as git submodules
- [ ] Change name of the slug to contest_slug in urls, middleware and mixins (remove mixins?) to avoid confusion with competition slug
- [ ] Packages handling permissions
# Dev
## User journey
### User profile
- [ ] My entries - make ready for multi-contests
- [X] Judge certification
- [ ] Judge applications
### Entry registration
- [ ] New coding (per competition)
- [ ] Recoding
- [ ] Entry registration journey could be more dynamic
- [ ] Old coding (1xxx should be per contest)
### Contest management
- [ ] Manage judges views (admin panel is not convenient)
## Security
- [ ] Currently unpublished competitions are accessible via direct urls...
## UI
- [x] Judge certification improvements
- [ ] Add contest banner on top on pages that are run in context of the contest
- [ ] User profile - participant data editing fix for consistent look & feel
## Email
- [ ] Async task
- [ ] Wyniki konkursu
- [ ] Judge application
# Translations
- [X] Judge application statuses
# Tests
- [ ] User factory - add judge profile
## Access
### Only translators can access
- [ ] Rosetta

## Admin actions
### Contest
- [x] Create duplicate(s)
### Judges
- [X] Accept/reject judge applications
 
# E2E tests
## Smoke
- [ ] Switching between multiple competitions on the first page
## Admin
- [ ] Create duplicate of contest
- [ ] Partners' logos, including in production (different path)
## User journeys
- [ ] Register as a judge journey
- [ ] Judge certiofication in context of contest application and in the profile 
## Organizers' journeys
- [ ] Select judging team

# Known issues
## Judge certification
- [ ] Judge can delete certification after he applied for judging