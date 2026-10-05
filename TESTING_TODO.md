# Frontend Testing TODO

Comprehensive testing checklist for VertretungsFlow frontend. Check off items as you complete them.

## ✅ Completed

- [x] Set up vitest infrastructure
- [x] Configure test environment (jsdom, setup files)
- [x] Add testing dependencies (@testing-library/react, jest-dom, user-event)
- [x] Create AbsenceTable component tests (9 tests)
- [x] Create App component smoke tests (6 tests)
- [x] Update GitLab CI to run tests
- [x] Fix React Router v7 future flag warnings
- [x] Create API Client tests (26 tests) - Integration/Contract tests
  - ✅ Token management, config setup, proxy mode switching
  - ✅ API endpoint URL construction, type definitions
  - ✅ Request configuration (nonce, withCredentials, FormData)
  - ✅ HTTP methods and download URL generation
  - ⚠️ **NOT covered:** Axios mocking, error handling (401/403/404/500), interceptors
  - 💡 **Note:** These are contract tests, not full unit tests with mocked axios behavior
- [x] Set up ESLint for code quality
- [x] Create Absence Wizard Step One tests (30 tests) - Form rendering, conditional fields, validation, submission
  - ✅ Form rendering (all fields, title, dropdowns, date pickers, period selectors)
  - ✅ Reason selection and all options
  - ✅ Conditional fields (excursion classes, personal reason) - show/hide/validation
  - ✅ Lesson/period selection with defaults (1-16)
  - ✅ Form validation (required fields, conditional validation, range validation, error clearing)
  - ✅ Form submission and error handling
  - ✅ Button behavior (rendering, clickability)
  - ⚠️ **Limitations:** Calendar date picker only tested at render level (not full date selection interaction)

**Current Status:** 71 tests passing ✨ + ESLint configured + Absence Wizard Step One fully tested

---

## ⚠️ Known Linting Warnings (Technical Debt)

**Status:** ESLint passes but with 18 warnings (0 errors) - all non-blocking

### React Hook Dependencies (2 warnings)
- [ ] `App.tsx:60` - `useEffect` missing `initializeApp` dependency (design choice)
- [ ] `CreateAbsence/StepTwo.tsx:32` - `useEffect` missing `fetchLessons` dependency (design choice)

### Console Statements (6 warnings)
- [ ] `components/FormDownloadButton.tsx:51` - `console.log` (change to `console.warn`)
- [ ] `pages/CreateAbsence/StepTwo.tsx:112, 141, 143, 226, 227, 231` - `console.log` statements (convert to `console.warn/error`)

### `any` Type Warnings (10 warnings) - Technical Debt
- [ ] `components/FormDownloadButton.tsx:52, 67` - Define proper types instead of `any`
- [ ] `pages/AbsenceDetail/index.tsx:41, 60, 76, 152` - Replace `any` with specific types
- [ ] `pages/Dashboard/PlannerView.tsx:33` - Type the response data
- [ ] `pages/Dashboard/TeacherView.tsx:22` - Type the response data
- [ ] `pages/Dashboard/index.tsx:17` - Type the response data

**Recommendation:** Address incrementally as features are refactored. Console warnings can be fixed quickly. `any` types require more investigation to determine proper types.

---

## 🎯 High Priority - Core Components

### Create Absence Wizard - Step Two (`src/pages/CreateAbsence/StepTwo.tsx`)

⚠️ **Testing Challenge:** This component has complex async loading states with artificial delays (setTimeout) that make synchronous testing difficult. Component needs refactoring to improve testability.

**Recommended Approach for Future:**
1. Extract loading logic into a custom hook (useAsyncLessons)
2. Mock the hook in tests instead of trying to manage timers
3. Or: Extract progress states into Context/state management for easier testing

**Features to Test (when refactored):**
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
- [ ] Test validation requiring notes OR "kann entfallen" for each lesson
- [ ] Test form submission with duplicate absence detection
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

**Testing Plan:** Comprehensive page with permission logic, conditional rendering, and user actions. Testing in 5 phases.

#### **Phase 1: Basic Rendering & States** ✅ (Foundation) - 11 tests passing
- [x] Test loading state displays spinner and "Lädt Abwesenheit..." message
- [x] Test error state displays error message and "Zurück zum Dashboard" button
- [x] Test "no ID" error state (missing absence ID in URL)
- [x] Test "not found" error state (absence doesn't exist)
- [x] Test successful data load renders main content
- [x] Test page title "Abwesenheit Details" is displayed
- [x] Test "Zurück zum Dashboard" button in header
- [x] Test API calls with correct parameters
- [x] Test loading to success state transition
- [x] Test loading to error state transition

#### **Phase 2: Permission Logic** (Core Authorization)
- [ ] Test admin role can see all action buttons (approve, complete, delete)
- [ ] Test planner role can see all action buttons
- [ ] Test dept_head role can see approve button
- [ ] Test dept_head can see complete button when config.deptHeadsCanComplete = true
- [ ] Test dept_head cannot see complete button when config.deptHeadsCanComplete = false
- [ ] Test teacher role cannot see any action buttons
- [ ] Test action buttons section hidden when user has no permissions

#### **Phase 3: Data Display & Conditional Fields** (Business Logic)
- [ ] Test teacher name displays (full_name or username)
- [ ] Test date range displays correctly (dd.MM.yyyy format)
- [ ] Test period range displays (start_period - end_period)
- [ ] Test absence reason label displays
- [ ] Test status badge renders with correct color and text (submitted/approved/rejected/completed/draft)
- [ ] Test conditional field: excursion_classes shown when reason="excursion"
- [ ] Test conditional field: excursion_classes hidden for other reasons
- [ ] Test conditional field: personal_reason shown when present
- [ ] Test conditional field: personal_reason hidden when not present
- [ ] Test conditional field: admin_notes shown when present
- [ ] Test conditional field: admin_notes hidden when empty
- [ ] Test created_at timestamp displays
- [ ] Test approved_at timestamp displays when status="approved"
- [ ] Test completed_at timestamp displays when status="completed"

#### **Phase 4: Affected Lessons Table** (Data Tables)
- [ ] Test affected lessons table renders with correct headers
- [ ] Test lesson count displays correctly (e.g., "Betroffene Stunden (3)")
- [ ] Test lesson data displays (date, period, subject, class_name)
- [ ] Test "Kann entfallen" column shown when reason !== "personal"
- [ ] Test "Kann entfallen" column hidden when reason = "personal"
- [ ] Test "Kann entfallen" badge shows "✓ Ja" when can_be_canceled = true
- [ ] Test "Kann entfallen" badge shows "- Nein" when can_be_canceled = false
- [ ] Test lesson notes display or "Keine Angaben" placeholder
- [ ] Test empty state: "Keine betroffenen Stunden" when no lessons
- [ ] Test period formatting for single period (e.g., "3")
- [ ] Test period formatting for range (e.g., "3-5")

#### **Phase 5: Attachments & Downloads** (File Handling)
- [ ] Test attachments section renders when attachments exist
- [ ] Test attachments section hidden when no attachments
- [ ] Test attachment count displays (e.g., "Anhänge (2)")
- [ ] Test attachment filename displays
- [ ] Test attachment file size displays (KB format)
- [ ] Test attachment upload timestamp displays
- [ ] Test download link has correct href (getAttachmentDownloadUrl)
- [ ] Test download button renders with "Download" text

#### **Phase 6: User Actions** (Interactions)
- [ ] Test approve button calls handleApprove(true) and reloads data
- [ ] Test reject button calls handleApprove(false) and reloads data
- [ ] Test approve button disabled when status="approved"
- [ ] Test reject button disabled when status="rejected"
- [ ] Test complete button calls handleComplete() and reloads data
- [ ] Test complete button disabled when status="completed"
- [ ] Test delete button shows confirmation dialog
- [ ] Test delete button navigates to dashboard after successful deletion
- [ ] Test delete confirmation can be cancelled
- [ ] Test action buttons show loading state during API calls
- [ ] Test error alerts display when API calls fail

#### **Phase 7: Navigation Between Absences** (Prev/Next)
- [ ] Test navigation buttons render when multiple absences exist
- [ ] Test navigation buttons hidden when only one absence
- [ ] Test "Zurück" button disabled when at first absence
- [ ] Test "Weiter →" button disabled when at last absence
- [ ] Test counter displays "X / Y" (current / total)
- [ ] Test "Zurück" button navigates to previous absence
- [ ] Test "Weiter →" button navigates to next absence
- [ ] Test navigation updates when absence ID changes in URL

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

## 🔬 Advanced API Client Tests (Optional Enhancement)

**Current Status:** Contract tests exist (26 tests). Full axios mocking tests would require refactoring.

**Future Enhancement Options:**
- [ ] Mock axios and test actual API call behavior
- [ ] Test error handling with mocked responses (401, 403, 404, 500)
- [ ] Test axios interceptors (request/response)
- [ ] Test retry logic on network failures
- [ ] Test request cancellation
- [ ] Test concurrent request handling
- [ ] Test rate limiting/throttling

**Note:** This would require refactoring the API client to be injectable/mockable.

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
