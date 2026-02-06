# Frontend Testing TODO

Comprehensive testing checklist for AbsenzFlow frontend. Check off items as you complete them.

## ✅ Completed

- [x] Set up vitest infrastructure
- [x] Configure test environment (jsdom, setup files)
- [x] Add testing dependencies (@testing-library/react, jest-dom, user-event)
- [x] Create AbsenceTable component tests (9 tests)
- [x] Create App component smoke tests (6 tests)
- [x] Update GitLab CI to run tests
- [x] Fix React Router v7 future flag warnings
- [x] Create API Client tests (26 tests) - Integration/Contract tests

**Current Status:** 41 tests passing ✨

---

## 🎯 High Priority - Core Components

### API Client (`src/api/client.ts`)
- [ ] Test `setBaseURL()` - URL configuration
- [ ] Test `setToken()` / `getToken()` - Token management
- [ ] Test `request()` method with different HTTP methods (GET, POST, PATCH, DELETE)
- [ ] Test proxy mode vs direct mode switching
- [ ] Test error handling (network errors, 401, 403, 404, 500)
- [ ] Test nonce header injection
- [ ] Test `withCredentials` in proxy mode
- [ ] Mock axios interceptors
- [ ] Test `getCurrentUser()` API call
- [ ] Test `createAbsence()`, `getAbsences()`, `updateAbsence()` calls

### Create Absence Wizard - Step One (`src/pages/CreateAbsence/StepOne.tsx`)
- [ ] Test form renders with all fields
- [ ] Test reason dropdown selection
- [ ] Test date picker interactions
- [ ] Test period selection (start/end)
- [ ] **Conditional Inputs:**
  - [ ] Test excursion classes field shows when reason="excursion"
  - [ ] Test excursion classes field hidden for other reasons
  - [ ] Test personal reason field shows when reason="personal"
  - [ ] Test personal reason field hidden for other reasons
- [ ] Test form validation (required fields)
- [ ] Test date range validation (end >= start)
- [ ] Test period validation (end >= start)
- [ ] Test "Weiter" button disabled when invalid
- [ ] Test "Weiter" button enabled when valid
- [ ] Test navigation to Step Two on submit

### Create Absence Wizard - Step Two (`src/pages/CreateAbsence/StepTwo.tsx`)
- [ ] Test lesson table renders correctly
- [ ] Test WebUntis lessons import
- [ ] Test "Stunden importieren" button
- [ ] Test lesson checkbox selection
- [ ] Test "Alle auswählen" / "Alle abwählen"
- [ ] Test "Kann entfallen" checkbox (conditional on reason)
- [ ] Test file upload button
- [ ] Test file upload validation (file type, size)
- [ ] Test file preview/list after upload
- [ ] Test file removal
- [ ] Test admin notes textarea
- [ ] Test "Zurück" button navigation
- [ ] Test "Absenden" button disabled when no lessons selected
- [ ] Test form submission
- [ ] Test success modal display

### Dashboard (`src/pages/Dashboard/index.tsx`)
- [ ] Test teacher view renders for teacher role
- [ ] Test planner view renders for planner role
- [ ] Test dept_head view renders correctly
- [ ] Test admin view renders correctly
- [ ] Test role-based component switching
- [ ] Test loading state

### Dashboard - Teacher View (`src/pages/Dashboard/TeacherView.tsx`)
- [ ] Test statistics cards render
- [ ] Test absences list loads
- [ ] Test calendar displays
- [ ] Test filtering by status
- [ ] Test absence click navigation to detail page
- [ ] Test "Neue Abwesenheit" button
- [ ] Test empty state

### Dashboard - Planner View (`src/pages/Dashboard/PlannerView.tsx`)
- [ ] Test all absences list renders
- [ ] Test filter by status
- [ ] Test filter by teacher
- [ ] Test filter by date range
- [ ] Test approve/reject actions
- [ ] Test bulk actions (if applicable)
- [ ] Test pagination

### Absence Detail (`src/pages/AbsenceDetail/index.tsx`)
- [ ] Test absence data displays correctly
- [ ] Test affected lessons table
- [ ] Test attachments section
- [ ] Test file download links
- [ ] Test conditional fields (excursion_classes, personal_reason)
- [ ] Test status badge rendering
- [ ] Test approve button (for dept_head/admin)
- [ ] Test complete button (for planner/admin)
- [ ] Test delete button (for owner/admin)
- [ ] Test permission-based button visibility
- [ ] Test PDF form download buttons
- [ ] Test admin notes display
- [ ] Test timeline/history (if implemented)

---

## 📊 Medium Priority - Dashboard Components

### Calendar Component (`src/components/dashboard/Calendar.tsx`)
- [ ] Test calendar grid renders
- [ ] Test month navigation (prev/next)
- [ ] Test today button
- [ ] Test absence markers on dates
- [ ] Test date click handler
- [ ] Test hover states
- [ ] Test multiple absences on same day
- [ ] Test weekend/holiday styling (if applicable)

### StatCard Component (`src/components/dashboard/StatCard.tsx`)
- [ ] Test card renders with title and value
- [ ] Test icon displays (if applicable)
- [ ] Test click handler
- [ ] Test loading state
- [ ] Test different stat types

### ToDoList Component (`src/components/dashboard/ToDoList.tsx`)
- [ ] Test empty state
- [ ] Test todo items render
- [ ] Test item click navigation
- [ ] Test status badges
- [ ] Test priority indicators (if applicable)
- [ ] Test mark as done

### DayAbsencesModal Component (`src/components/dashboard/DayAbsencesModal.tsx`)
- [ ] Test modal opens/closes
- [ ] Test absences list for selected day
- [ ] Test modal title shows correct date
- [ ] Test absence click in modal
- [ ] Test empty state
- [ ] Test close button/overlay click

### AbsencesListModal Component (`src/components/dashboard/AbsencesListModal.tsx`)
- [ ] Test modal opens/closes
- [ ] Test absences list renders
- [ ] Test filtering in modal
- [ ] Test absence selection
- [ ] Test pagination in modal

### AbsenceSuccessModal Component (`src/components/AbsenceSuccessModal.tsx`)
- [ ] Test modal displays after successful absence creation
- [ ] Test success message
- [ ] Test "Zur Übersicht" button
- [ ] Test "Weitere Abwesenheit erstellen" button
- [ ] Test modal closes properly

### FormDownloadButton Component (`src/components/FormDownloadButton.tsx`)
- [ ] Test button renders with correct label
- [ ] Test PDF generation trigger
- [ ] Test loading state during generation
- [ ] Test error handling
- [ ] Test download initiates
- [ ] Test disabled state

---

## 🔧 Low Priority - Utilities & Helpers

### Constants (`src/constants.ts`)
- [ ] Test `getAbsenceReasonLabel()` returns correct labels
- [ ] Test `getAbsenceReasonLabel()` handles unknown reasons
- [ ] Test `getAvailableFormsForReason()` returns correct forms
- [ ] Test PDF_FORMS mapping completeness

### Type Definitions (`src/types/index.ts`)
- [ ] Validate TypeScript types match backend schemas
- [ ] Test type guards (if any)
- [ ] Ensure all API responses match types

### Date Utilities (if extracted)
- [ ] Test date formatting functions
- [ ] Test date parsing
- [ ] Test period time formatting
- [ ] Test date range calculations

---

## 🔄 Integration Tests

### Absence Creation Flow
- [ ] Test complete flow: Dashboard → Create → Step1 → Step2 → Submit → Success
- [ ] Test flow with file upload
- [ ] Test flow with excursion conditional fields
- [ ] Test flow with personal reason conditional fields
- [ ] Test cancellation at various steps
- [ ] Test validation errors at each step

### Absence Approval Workflow
- [ ] Test dept_head approves absence
- [ ] Test planner completes absence
- [ ] Test rejection flow
- [ ] Test status transitions
- [ ] Test email notifications triggered (mock)

### File Upload/Download Flow
- [ ] Test file upload during absence creation
- [ ] Test file list display in detail view
- [ ] Test file download
- [ ] Test file deletion
- [ ] Test files deleted when absence completed

### WebUntis Integration
- [ ] Test lesson import button
- [ ] Test API call to fetch lessons
- [ ] Test lesson data population in table
- [ ] Test loading state
- [ ] Test error handling (API down, no lessons)

---

## 🛡️ Edge Cases & Error Handling

### Error Scenarios
- [ ] Test API network errors (offline)
- [ ] Test 401 unauthorized handling
- [ ] Test 403 forbidden handling
- [ ] Test 404 not found handling
- [ ] Test 500 server error handling
- [ ] Test timeout handling
- [ ] Test invalid token handling
- [ ] Test session expiry

### Validation Edge Cases
- [ ] Test empty form submission attempts
- [ ] Test invalid date ranges (end before start)
- [ ] Test invalid period ranges
- [ ] Test file upload size limits
- [ ] Test file upload type restrictions
- [ ] Test special characters in text fields
- [ ] Test very long text inputs
- [ ] Test XSS prevention in user inputs

### Boundary Conditions
- [ ] Test with 0 absences
- [ ] Test with 100+ absences (performance)
- [ ] Test with very long absence notes
- [ ] Test with many file attachments
- [ ] Test with all lessons selected
- [ ] Test with no lessons available

---

## 🎨 Accessibility Tests (Bonus)

- [ ] Test keyboard navigation
- [ ] Test screen reader labels (aria-labels)
- [ ] Test focus management in modals
- [ ] Test form error announcements
- [ ] Test button states (disabled, loading)
- [ ] Test color contrast
- [ ] Test responsive design (mobile, tablet, desktop)

---

## 📈 Coverage Goals

**Target Coverage:**
- [ ] 80%+ line coverage
- [ ] 80%+ branch coverage
- [ ] 100% coverage for utility functions
- [ ] 90%+ coverage for core business logic

**Generate Coverage Report:**
```bash
cd wordpress-plugin
npm run test -- --coverage
```

---

## 🚀 Performance Tests (Advanced)

- [ ] Test large dataset rendering (100+ absences)
- [ ] Test calendar with many events
- [ ] Test file upload progress
- [ ] Test API request debouncing
- [ ] Test lazy loading

---

## 📝 Notes

### Testing Best Practices
1. **Arrange-Act-Assert** pattern for test structure
2. Use **data-testid** sparingly (prefer semantic queries)
3. Test user behavior, not implementation details
4. Mock external dependencies (API, time, file system)
5. Keep tests isolated and independent
6. Use descriptive test names

### Useful Commands
```bash
# Run all tests
npm run test

# Run tests in watch mode
npm run test -- --watch

# Run tests with UI
npm run test:ui

# Run specific test file
npm run test -- AbsenceTable.test.tsx

# Run tests with coverage
npm run test -- --coverage

# Run tests matching pattern
npm run test -- --testNamePattern="renders correctly"
```

### Resources
- [Vitest Docs](https://vitest.dev/)
- [Testing Library Docs](https://testing-library.com/docs/react-testing-library/intro/)
- [Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)

---

**Last Updated:** 2026-02-06
**By:** Claude Sonnet 4.5 (with User Seyfried)
