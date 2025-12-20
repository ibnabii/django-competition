# Fixes
- [ ] Allauth now does not set username to login from before @, resulting in blank name https://chatgpt.com/c/694428e2-c238-832c-8a6f-233adc497be3
- [ ] W zgłoszeniach jest dostepna ikona wyników
# Refactoring
- [ ] Use ContextContextMixin where contest context is required
- [ ] Co się stanie z danymi jak zostanie usunięte kjonto użytkownika?
# Dev
## User journey
### User profile
- [ ] My entries - make ready for multi-contests
- [ ] Judge certification
- [ ] Judge applications
## Security
- [ ] Currently unpublished competitions are accessible via direct urls...
## UI
- [x] Judge certification improvements
- [ ] Add contest banner on top on pages that are run in context of the contest
# Tests
## Access
### Only translators can access
- [ ] Rosetta

## Admin actions
### Contest
- [x] Create duplicate(s)

# E2E tests
## Smoke
- [ ] Switching between multiple competitions on the first page
## Admin
- [ ] Create duplicate of contest
- [ ] Partners' logos, including in production (different path)
## User journeys
- [ ] Register as a judge journey
## Organizers' journeys
- [ ] Select judging team

# Known issues
## Judge certification
- [ ] Judge can delete certification after he applied for judging