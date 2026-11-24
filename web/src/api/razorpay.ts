interface PaymentConfirmation {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
}

interface CheckoutOrder {
  key: string
  order_id: string
  amount: number
  currency: string
  name: string
  description: string
  prefill?: { name: string; email?: string; contact?: string }
}

type CheckoutConstructor = new (
  options: CheckoutOrder & {
    handler: (confirmation: PaymentConfirmation) => void
    modal: { ondismiss: () => void }
  },
) => { open: () => void }

type CheckoutWindow = Window & { Razorpay?: CheckoutConstructor }
let loadingCheckout: Promise<CheckoutConstructor> | undefined

function loadCheckout(): Promise<CheckoutConstructor> {
  const checkoutWindow = window as CheckoutWindow
  if (checkoutWindow.Razorpay) return Promise.resolve(checkoutWindow.Razorpay)

  loadingCheckout ??= new Promise<CheckoutConstructor>((resolve, reject) => {
    const script = document.createElement('script')
    const fail = () => {
      clearTimeout(timeout)
      script.remove()
      reject(new Error('Razorpay Checkout could not load. Please try again.'))
    }
    const timeout = window.setTimeout(fail, 15000)
    script.onload = () => {
      const Razorpay = checkoutWindow.Razorpay
      if (!Razorpay) {
        fail()
        return
      }
      clearTimeout(timeout)
      resolve(Razorpay)
    }
    script.onerror = fail
    script.src = 'https://checkout.razorpay.com/v1/checkout.js'
    document.head.appendChild(script)
  }).catch((error) => {
    loadingCheckout = undefined
    throw error
  })

  return loadingCheckout
}

export async function openRazorpayCheckout(order: CheckoutOrder): Promise<PaymentConfirmation | null> {
  if (order.order_id.startsWith('order_mock_')) {
    throw new Error('Online payments are unavailable until Razorpay is configured.')
  }
  const Razorpay = await loadCheckout()
  return new Promise((resolve, reject) => {
    const checkout = new Razorpay({
      ...order,
      handler: (confirmation) => {
        if (
          confirmation.razorpay_order_id !== order.order_id ||
          !confirmation.razorpay_payment_id ||
          !confirmation.razorpay_signature
        ) {
          reject(new Error('Razorpay returned an invalid payment confirmation.'))
          return
        }
        resolve(confirmation)
      },
      modal: { ondismiss: () => resolve(null) },
    })
    checkout.open()
  })
}
