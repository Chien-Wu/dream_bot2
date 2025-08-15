# Testing Workflow for Simplified Message Architecture

## Quick Start
```bash
# Run all tests
python test_simplified_architecture.py

# Or run specific test categories
python test_simplified_architecture.py --category line_service
python test_simplified_architecture.py --category message_processor
python test_simplified_architecture.py --category integration
```

## Test Categories

### 1. LineService Functionality
**What it tests**: Message sending, text processing, fallback logic

**Manual verification**:
- Text cleaning (removes reference brackets)
- Text splitting by sentence endings
- Reply → Push fallback
- Handover detection

### 2. MessageProcessor Chain
**What it tests**: Handler chain execution, message routing

**Manual verification**:
- Image message handling
- Admin command routing
- Welcome flow processing
- Handover requests
- AI response generation

### 3. Integration Flow
**What it tests**: End-to-end message processing

**Manual verification**:
- Complete message flow
- Error handling
- Logging verification

## Test Scenarios

### A. Text Processing Tests
1. **Reference cleaning**: `Hello【1:2†source】world` → `Helloworld`
2. **Chinese semicolon**: `First；Second` → `First\nSecond`
3. **Sentence splitting**: `Hello. World! How?` → `['Hello.', 'World!', 'How?']`
4. **Long text handling**: Multi-sentence messages split correctly

### B. Message Flow Tests
1. **Image messages** → Admin notification
2. **Admin commands** → Raw message sending (admin users only)
3. **Handover requests** → Admin notification + user confirmation
4. **Normal messages** → AI processing + formatted response

### C. Fallback Tests
1. **Valid reply token** → Reply + Push for additional segments
2. **Invalid reply token** → Automatic fallback to Push
3. **Network errors** → Proper error handling and logging

### D. Error Scenarios
1. **AI service failures** → Error message to user
2. **LINE API failures** → Graceful degradation
3. **Database errors** → Proper logging and user notification

## Live Testing Checklist

### Prerequisites
- [ ] Environment variables configured
- [ ] Database accessible
- [ ] OpenAI API key valid
- [ ] LINE Bot webhook configured

### Test Execution
- [ ] Run automated test suite
- [ ] Verify all tests pass
- [ ] Check log output for errors
- [ ] Review test coverage report

### Manual Verification
- [ ] Send test message via LINE
- [ ] Verify response received
- [ ] Check admin notifications work
- [ ] Test image message handling
- [ ] Verify handover requests

## Expected Results

### ✅ Success Indicators
- All automated tests pass
- No error logs during normal operation
- Messages sent/received correctly
- Proper fallback behavior
- Admin notifications work
- Text formatting preserved

### ❌ Failure Indicators
- Test failures or timeouts
- Error logs during message processing
- Messages not delivered
- Formatting issues
- Admin notifications missing
- Fallback not working

## Rollback Plan
If tests fail:
1. **Document specific failures**
2. **Check git status**: `git status`
3. **Rollback if needed**: `git checkout HEAD~1`
4. **Report issues** with specific error messages

## Performance Verification
- [ ] Message processing time < 2 seconds
- [ ] No memory leaks in long-running tests
- [ ] Concurrent message handling works
- [ ] Database connection pooling stable

## Production Readiness
- [ ] All tests pass
- [ ] Error handling verified
- [ ] Logging appropriate (not too verbose)
- [ ] Configuration validated
- [ ] Monitoring alerts configured