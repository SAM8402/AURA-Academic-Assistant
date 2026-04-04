<template>
  <div class="login-wrapper">
    <div class="login-box">

      <!--  Left Section -->
      <div class="left-section">
        <div class="text-content">
          <h1>Welcome to AURA</h1>
          <p class="lead">
            Your personalized academic assistant for track, analyze, and enhance your learning journey.
          </p>
          <!-- <p class="small">
            Empowering students with insights and tools to excel in their academic pursuits.
          </p> -->
        </div>
      </div>

      <!-- Right Section -->
      <div class="right-section">
        <div class="form-content">
          <div class="text-end mb-3">
            <small class="text-muted">
              New here?
              <router-link to="/register" class="text-primary fw-semibold text-decoration-none">
                Sign up
              </router-link>
            </small>
          </div>

          <h2 class="text-primary fw-bold mb-2">Sign in to AURA</h2>
          <p class="text-muted mb-4">Your academic dashboard awaits.</p>

          <!-- Error Message -->
          <div v-if="errorMessage" class="alert alert-danger alert-dismissible fade show" role="alert">
            {{ errorMessage }}
            <button type="button" class="btn-close" @click="errorMessage = ''"></button>
          </div>

          <!-- Success Message -->
          <div v-if="successMessage" class="alert alert-success alert-dismissible fade show" role="alert">
            {{ successMessage }}
            <button type="button" class="btn-close" @click="successMessage = ''"></button>
          </div>

          <form @submit.prevent="handleLogin">
            <div class="mb-3">
              <input
                type="email"
                class="form-control rounded-pill"
                placeholder="IITM email"
                v-model="email"
                required
              />
            </div>
            <div class="mb-4">
              <input
                type="password"
                class="form-control rounded-pill"
                placeholder="Password"
                v-model="password"
                required
              />
            </div>

            <button
              type="submit"
              class="btn btn-gradient rounded-pill w-100 mb-3 fw-semibold"
              :disabled="loading"
            >
              <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
              {{ loading ? 'Signing in...' : 'Sign in' }}
            </button>

            <!-- <p class="text-center text-muted small mb-3">or continue with</p> -->

            <!-- <div class="d-flex justify-content-center gap-2">
              <button type="button" class="btn btn-outline-primary rounded-pill w-50" disabled>
                <i class="bi bi-google me-1"></i> Google
              </button>
              <button type="button" class="btn btn-outline-primary rounded-pill w-50" disabled>
                <i class="bi bi-facebook me-1"></i> Facebook
              </button>
            </div> -->
            <p class="text-center text-muted small mt-2">(Social login coming soon)</p>
          </form>
        </div>
      </div>

    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

export default {
  name: 'LoginPage',
  setup() {
    const router = useRouter()
    const userStore = useUserStore()

    const email = ref('')
    const password = ref('')
    const loading = ref(false)
    const errorMessage = ref('')
    const successMessage = ref('')

    const handleLogin = async () => {
      // Clear previous messages
      errorMessage.value = ''
      successMessage.value = ''

      // Validation
      if (!email.value || !password.value) {
        errorMessage.value = 'Please fill in all fields'
        return
      }

      loading.value = true

      try {
        // Call login action from store
        const result = await userStore.login(email.value, password.value)

        if (result.success) {
          successMessage.value = 'Login successful! Redirecting...'

          // Redirect based on role
          setTimeout(() => {
            const role = userStore.role
            if (role === 'admin') {
              router.push('/admin/dashboard')
            } else if (role === 'instructor') {
              router.push('/instructor/dashboard')
            } else if (role === 'ta') {
              router.push('/ta/dashboard')
            } else {
              router.push('/student/dashboard')
            }
          }, 1000)
        } else {
          errorMessage.value = result.error || 'Login failed. Please try again.'
        }
      } catch (error) {
        errorMessage.value = 'An error occurred. Please check your connection and try again.'
        console.error('Login error:', error)
      } finally {
        loading.value = false
      }
    }

    return {
      email,
      password,
      loading,
      errorMessage,
      successMessage,
      handleLogin
    }
  }
}
</script>

<style scoped>
/* Page background */
.login-wrapper {
  background: #9ac6f2;
  height: 100dvh;
  display: flex;
  justify-content: center;
  align-items: center;
}

/* Main login box */
.login-box {
  display: flex;
  flex-direction: row;
  width: 1000px; /* fixed width */
  height: 600px; /* fixed height */
  border-radius: 1.5rem;
  overflow: hidden;
  background: #dcd8d8;
  box-shadow: 0 8px 35px rgba(0, 0, 0, 0.3);
}

/* Left Section */
.left-section {
  width: 50%;
  background: #182633;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 2.5rem;
}

.text-content {
  background: rgb(255, 255, 255);
  padding: 2rem;
  border-radius: 1rem;
  text-align: center;
  width: 85%;
  max-width: 450px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
}

.text-content h1 {
  color: #000000c7;
  font-weight: 800;
  font-size: 2.2rem;
  margin-bottom: 1rem;
}

.text-content .lead {
  color: #212121;
  font-size: 1.1rem;
  margin-bottom: 1rem;
}

.text-content .small {
  font-size: 0.95rem;
  color: #424242;
}

/* Right Section */
.right-section {
  width: 50%;
  display: flex;
  color: #000000;
  justify-content: center;
  align-items: center;
  padding: 3rem;
}

.form-content {
  width: 100%;
  max-width: 360px;
    
}

/* Buttons */
.btn-gradient {
  background: linear-gradient(135deg, #1976d2, #004ba0);
  border: none;
  color: rgb(255, 255, 255);
  font-size: 1.05rem;
  padding: 0.75rem;
  transition: all 0.3s ease;
}

.btn-gradient:hover {
  background: linear-gradient(135deg, #0d47a1, #002b7a);
  transform: scale(1.03);
}

/* Inputs */
input.form-control {
  padding: 0.9rem 1.1rem;
  border: 1px solid var(--input-border, #dee2e6);
  font-size: 1rem;
  background-color: var(--input-bg, #fff);
  color: var(--input-text, #1a1a1a);
}

input.form-control:focus {
  border-color: var(--input-focus, #1976d2);
  box-shadow: 0 0 0 3px rgba(25, 118, 210, 0.15);
  outline: none;
}

/* Prevent auto shrink on zoom */
* {
  flex-shrink: 0;
}

/* Responsive for small screens */
@media (max-width: 992px) {
  .login-box {
    flex-direction: column;
    width: 95%;
    height: auto;
  }

  .left-section {
    width: 100%;
    height: 250px;
    padding: 1.5rem;
  }

  .text-content {
    width: 100%;
    padding: 1.5rem;
  }

  .right-section {
    width: 100%;
    padding: 2rem 1.5rem;
  }
}
</style>
