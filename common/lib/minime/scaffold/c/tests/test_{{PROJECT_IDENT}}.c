#include "unity.h"

#include "{{PROJECT_NAME}}.h"

void setUp(void) {}
void tearDown(void) {}

static void test_name_is_project_name(void)
{
    TEST_ASSERT_EQUAL_STRING("{{PROJECT_NAME}}", {{PROJECT_IDENT}}_name());
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_name_is_project_name);
    return UNITY_END();
}
