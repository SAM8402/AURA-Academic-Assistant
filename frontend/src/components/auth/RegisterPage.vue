<template>
  <div class="signup-wrapper d-flex align-items-center justify-content-center">
    <div class="container-fluid d-flex justify-content-center align-items-center">
      <div class="row big-card shadow-lg rounded-4 overflow-hidden">
        
        <!-- Left Side -->
        <div class="col-lg-6 col-md-5 left-section d-flex flex-column justify-content-center align-items-center">
          <div class="text-content text-center">
            <h1 class="fw-bold mb-3 display-6" :style="{ color: 'var(--text-primary)' }">Join AURA Today</h1>
            <p class="lead fw-medium mb-3" :style="{ color: 'var(--text-secondary)' }">
              Explore personalized learning tools and study smarter with AURA.
            </p>
          </div>
        </div>

        <!-- Right Side -->
        <div class="col-lg-6 col-md-7 form-section d-flex flex-column justify-content-center align-items-center" :style="{ background: 'var(--bg-secondary)', borderLeft: '1px solid var(--border-default)' }">
          <div class="form-container p-4 p-md-5 w-100" style="max-width: 420px;">
            <div class="text-end mb-3">
              <small :style="{ color: 'var(--text-tertiary)' }">
                Already a user?
                <router-link to="/login" class="fw-semibold text-decoration-none" :style="{ color: 'var(--accent-blue)' }">Sign in</router-link>
              </small>
            </div>

            <h3 class="fw-bold mb-2 text-center" :style="{ color: 'var(--text-primary)' }">Create your account</h3>
            <p class="mb-4 text-center" :style="{ color: 'var(--text-secondary)' }">Get started with premium features</p>

            <!-- Error Message -->
            <div v-if="errorMessage" class="alert alert-danger alert-dismissible fade show" role="alert">
              {{ errorMessage }}
              <button type="button" class="btn-close" @click="errorMessage = ''" aria-label="Close"></button>
            </div>

            <!-- Success Message -->
            <div v-if="successMessage" class="alert alert-success alert-dismissible fade show" role="alert">
              {{ successMessage }}
              <button type="button" class="btn-close" @click="successMessage = ''" aria-label="Close"></button>
            </div>

            <form @submit.prevent="handleRegister">
              <div class="mb-3">
                <input
                  type="text"
                  class="form-control rounded-pill fs-6"
                  placeholder="Your full name"
                  v-model="fullName"
                  required
                  aria-label="Full name"
                />
              </div>
              <div class="mb-3">
                <input
                  type="email"
                  class="form-control rounded-pill fs-6"
                  placeholder="IITM email"
                  v-model="email"
                  required
                  aria-label="Email address"
                />
              </div>
              <div class="mb-3">
                <input
                  type="password"
                  class="form-control rounded-pill fs-6"
                  placeholder="Create password (min 8 characters)"
                  v-model="password"
                  required
                  minlength="8"
                  aria-label="Password"
                />
              </div>
              <div class="mb-4">
                <input
                  type="password"
                  class="form-control rounded-pill fs-6"
                  placeholder="Confirm password"
                  v-model="confirmPassword"
                  required
                  aria-label="Confirm password"
                />
              </div>
              <div class="mb-4">
                <select class="form-select rounded-pill fs-6" v-model="role" @change="onRoleChange" required aria-label="Select your role">
                  <option value="" disabled selected>Select your role</option>
                  <option value="student">Student</option>
                  <option value="ta">Teaching Assistant (TA)</option>
                  <option value="instructor">Instructor</option>
                </select>
              </div>

              <!-- Course Selection (visible only for TA/Instructor) -->
              <div v-if="role === 'ta' || role === 'instructor'" class="mb-4">
                <label class="form-label fw-semibold mb-2" :style="{ color: 'var(--text-primary)' }">Select Courses</label>
                <div class="border rounded-3 p-3" style="max-height: 200px; overflow-y: auto;" :style="{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--border-default)' }">
                  <div v-if="loadingCourses" class="text-center py-3">
                    <div class="spinner-border spinner-border-sm" :style="{ color: 'var(--accent-blue)' }"></div>
                    <p class="mt-2 small" :style="{ color: 'var(--text-tertiary)' }">Loading courses...</p>
                  </div>
                  <div v-else-if="courses.length === 0" class="text-center py-3">
                    <p class="small" :style="{ color: 'var(--text-tertiary)' }">No courses available</p>
                  </div>
                  <div v-else class="space-y-2">
                    <div v-for="course in courses" :key="course.id" class="form-check">
                      <input
                        type="checkbox"
                        :id="`course-${course.id}`"
                        class="form-check-input"
                        :value="course.id"
                        v-model="selectedCourses"
                      />
                      <label :for="`course-${course.id}`" class="form-check-label" :style="{ color: 'var(--text-primary)' }">
                        {{ course.name }}
                        <small v-if="course.description" class="d-block" :style="{ color: 'var(--text-tertiary)' }">{{ course.description }}</small>
                      </label>
                    </div>
                  </div>
                </div>
                <small v-if="role === 'ta' || role === 'instructor'" class="d-block mt-2" :style="{ color: 'var(--accent-red)' }">
                  <strong>Required:</strong> Select at least one course
                </small>
              </div>

              <button
                type="submit"
                class="btn rounded-pill w-100 mb-3 fw-semibold fs-5 text-white"
                :disabled="loading"
                :style="{ background: loading ? 'var(--text-muted)' : 'linear-gradient(135deg, var(--accent-blue), #004ba0)', border: 'none', minHeight: '48px' }"
              >
                <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                {{ loading ? 'Creating account...' : 'Sign up' }}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getAllCourses } from '@/api/courses'

export default {
  name: 'RegisterPage',
  setup() {
    const router = useRouter()
    const userStore = useUserStore()

    const fullName = ref('')
    const email = ref('')
    const password = ref('')
    const confirmPassword = ref('')
    const role = ref('')
    const loading = ref(false)
    const errorMessage = ref('')
    const successMessage = ref('')
    const courses = ref([])
    const selectedCourses = ref([])
    const loadingCourses = ref(false)

    onMounted(async () => {
      try {
        loadingCourses.value = true
        const response = await getAllCourses()
        courses.value = Array.isArray(response) ? response : response.courses || []
      } catch (error) {
        console.error('Failed to load courses:', error)
        courses.value = []
      } finally {
        loadingCourses.value = false
      }
    })

    const onRoleChange = async () => {
      if (role.value === 'ta' || role.value === 'instructor') {
        if (courses.value.length === 0 && !loadingCourses.value) {
          try {
            loadingCourses.value = true
            const response = await getAllCourses()
            courses.value = Array.isArray(response) ? response : response.courses || []
          } catch (error) {
            console.error('Failed to load courses:', error)
            errorMessage.value = 'Failed to load courses. Please try again.'
          } finally {
            loadingCourses.value = false
          }
        }
        selectedCourses.value = []
      } else {
        selectedCourses.value = []
      }
    }

    const handleRegister = async () => {
      errorMessage.value = ''
      successMessage.value = ''

      if (!fullName.value || !email.value || !password.value || !confirmPassword.value || !role.value) {
        errorMessage.value = 'Please fill in all fields'
        return
      }

      if (password.value.length < 8) {
        errorMessage.value = 'Password must be at least 8 characters long'
        return
      }

      if (password.value !== confirmPassword.value) {
        errorMessage.value = 'Passwords do not match'
        return
      }

      if ((role.value === 'ta' || role.value === 'instructor') && selectedCourses.value.length === 0) {
        errorMessage.value = `Please select at least one course for ${role.value} role`
        return
      }

      loading.value = true

      try {
        const result = await userStore.register(
          email.value,
          password.value,
          role.value,
          fullName.value,
          selectedCourses.value
        )

        if (result.success) {
          successMessage.value = 'Registration successful! Redirecting to dashboard...'

          setTimeout(() => {
            const userRole = userStore.role
            if (userRole === 'admin') {
              router.push('/admin/dashboard')
            } else if (userRole === 'instructor') {
              router.push('/instructor/dashboard')
            } else if (userRole === 'ta') {
              router.push('/ta/dashboard')
            } else {
              router.push('/student/dashboard')
            }
          }, 1000)
        } else {
          errorMessage.value = result.error || 'Registration failed. Please try again.'
        }
      } catch (error) {
        errorMessage.value = 'An error occurred. Please check your connection and try again.'
        console.error('Registration error:', error)
      } finally {
        loading.value = false
      }
    }

    return {
      fullName,
      email,
      password,
      confirmPassword,
      role,
      loading,
      errorMessage,
      successMessage,
      courses,
      selectedCourses,
      loadingCourses,
      onRoleChange,
      handleRegister
    }
  }
}
</script>

<style scoped>
.signup-wrapper {
  background: var(--bg-tertiary);
  min-height: 100dvh;
  width: 100%;
  overflow: hidden;
}

.big-card {
  width: 90%;
  max-width: 1100px;
  background: var(--card-bg);
  border-radius: 1.5rem;
  box-shadow: 0 10px 40px var(--card-shadow);
}

.left-section {
  background: var(--bg-primary);
  min-height: 60dvh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.left-section .text-content {
  background: var(--bg-secondary);
  padding: 2.5rem;
  border-radius: 1rem;
  box-shadow: 0 4px 15px var(--card-shadow);
  width: 85%;
  text-align: center;
}

/* Responsive */
@media (max-width: 992px) {
  .big-card {
    flex-direction: column;
  }
  .left-section {
    min-height: 30dvh;
  }
}

@media (max-width: 768px) {
  .left-section {
    display: none;
  }
  .form-section {
    flex: 1 1 100%;
  }
}
</style>
