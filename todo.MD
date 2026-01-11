# Fixes
- [ ] Allauth now does not set username to login from before @, resulting in blank name https://chatgpt.com/c/694428e2-c238-832c-8a6f-233adc497be3
- [ ] W zgłoszeniach jest dostepna ikona wyników
## Multicompetition
- [ ] Results
- [ ] Admin panel - participants
# Refactoring
- [ ] Use ContestContextMixin where contest context is required
- [ ] Co się stanie z danymi jak zostanie usunięte konto użytkownika?
- [ ] Cleanup requirements
- [ ] Modify Style-Category-Contest - maybe Category should feature it's own name, not necesarly a copy fo the style?
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