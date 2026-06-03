

package com.pps.costio

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.util.Log
import com.android.billingclient.api.*
import io.flutter.embedding.android.FlutterActivity
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

class MainActivity : FlutterActivity(), PurchasesUpdatedListener {

    private lateinit var billingClient: BillingClient

    private var pendingUserId: String? = null
    private var pendingWorkspaceId: String? = null
    private var pendingProductId: String? = null
    private var pendingPlanType: String? = null

    companion object {
        private const val TAG = "CostioBilling"

        // آدرس Railway backend خودت
        private const val BACKEND_URL = "https://web-production-3868c.up.railway.app"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setupBillingClient()
        handleIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }

    private fun setupBillingClient() {
        billingClient = BillingClient.newBuilder(this)
            .setListener(this)
            .enablePendingPurchases(
                PendingPurchasesParams.newBuilder()
                    .enableOneTimeProducts()
                    .build()
            )
            .build()

        billingClient.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(billingResult: BillingResult) {
                Log.d(TAG, "Billing setup result: ${billingResult.responseCode}")

                if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                    Log.d(TAG, "Billing client is ready")
                } else {
                    Log.e(TAG, "Billing setup failed: ${billingResult.debugMessage}")
                }
            }

            override fun onBillingServiceDisconnected() {
                Log.w(TAG, "Billing service disconnected")
            }
        })
    }

    private fun handleIntent(intent: Intent?) {
        val data: Uri = intent?.data ?: return

        Log.d(TAG, "Deep link received: $data")

        if (data.scheme != "costio") return
        if (data.host != "buy") return

        val productId = data.getQueryParameter("product_id")
        val planType = data.getQueryParameter("plan_type")
        val userId = data.getQueryParameter("user_id")
        val workspaceId = data.getQueryParameter("workspace_id")

        if (productId.isNullOrBlank() || userId.isNullOrBlank()) {
            Log.e(TAG, "Missing product_id or user_id")
            return
        }

        pendingProductId = productId
        pendingPlanType = planType
        pendingUserId = userId
        pendingWorkspaceId = workspaceId

        startPurchase(productId)
    }

    private fun startPurchase(productId: String) {
        if (!::billingClient.isInitialized) {
            Log.e(TAG, "Billing client is not initialized")
            return
        }

        if (!billingClient.isReady) {
            Log.w(TAG, "Billing client is not ready. Reconnecting...")

            billingClient.startConnection(object : BillingClientStateListener {
                override fun onBillingSetupFinished(billingResult: BillingResult) {
                    if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                        queryProductAndLaunch(productId)
                    } else {
                        Log.e(TAG, "Reconnect failed: ${billingResult.debugMessage}")
                    }
                }

                override fun onBillingServiceDisconnected() {
                    Log.w(TAG, "Billing service disconnected again")
                }
            })

            return
        }

        queryProductAndLaunch(productId)
    }

    private fun queryProductAndLaunch(productId: String) {
        val product = QueryProductDetailsParams.Product.newBuilder()
            .setProductId(productId)
            .setProductType(BillingClient.ProductType.SUBS)
            .build()

        val params = QueryProductDetailsParams.newBuilder()
            .setProductList(listOf(product))
            .build()

        billingClient.queryProductDetailsAsync(params) { billingResult, productDetailsResult ->
            if (billingResult.responseCode != BillingClient.BillingResponseCode.OK) {
                Log.e(TAG, "Query product failed: ${billingResult.debugMessage}")
                return@queryProductDetailsAsync
            }

            val productDetailsList = productDetailsResult.productDetailsList

            if (productDetailsList.isNullOrEmpty()) {
                Log.e(TAG, "Product not found in Google Play: $productId")
                return@queryProductDetailsAsync
            }

            val productDetails = productDetailsList[0]

            val offerToken = productDetails.subscriptionOfferDetails
                ?.firstOrNull()
                ?.offerToken

            if (offerToken.isNullOrBlank()) {
                Log.e(TAG, "No offer token found for subscription: $productId")
                return@queryProductDetailsAsync
            }

            val productDetailsParams = BillingFlowParams.ProductDetailsParams.newBuilder()
                .setProductDetails(productDetails)
                .setOfferToken(offerToken)
                .build()

            val billingFlowParams = BillingFlowParams.newBuilder()
                .setProductDetailsParamsList(listOf(productDetailsParams))
                .build()

            val launchResult = billingClient.launchBillingFlow(this, billingFlowParams)

            Log.d(TAG, "Launch billing flow result: ${launchResult.responseCode}")
        }
    }

    override fun onPurchasesUpdated(
        billingResult: BillingResult,
        purchases: MutableList<Purchase>?
    ) {
        Log.d(TAG, "Purchase updated: ${billingResult.responseCode}")

        when (billingResult.responseCode) {
            BillingClient.BillingResponseCode.OK -> {
                if (!purchases.isNullOrEmpty()) {
                    for (purchase in purchases) {
                        handlePurchase(purchase)
                    }
                }
            }

            BillingClient.BillingResponseCode.USER_CANCELED -> {
                Log.d(TAG, "User canceled purchase")
            }

            else -> {
                Log.e(TAG, "Purchase failed: ${billingResult.debugMessage}")
            }
        }
    }

    private fun handlePurchase(purchase: Purchase) {
        Log.d(TAG, "Purchase token: ${purchase.purchaseToken}")

        if (purchase.purchaseState == Purchase.PurchaseState.PURCHASED) {
            if (!purchase.isAcknowledged) {
                acknowledgePurchase(purchase)
            }

            sendPurchaseToBackend(purchase)
        } else {
            Log.w(TAG, "Purchase is not completed yet")
        }
    }

    private fun acknowledgePurchase(purchase: Purchase) {
        val params = AcknowledgePurchaseParams.newBuilder()
            .setPurchaseToken(purchase.purchaseToken)
            .build()

        billingClient.acknowledgePurchase(params) { billingResult ->
            if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                Log.d(TAG, "Purchase acknowledged")
            } else {
                Log.e(TAG, "Acknowledge failed: ${billingResult.debugMessage}")
            }
        }
    }

    private fun sendPurchaseToBackend(purchase: Purchase) {
        val userId = pendingUserId
        val productId = pendingProductId
        val planType = pendingPlanType ?: ""

        if (userId.isNullOrBlank() || productId.isNullOrBlank()) {
            Log.e(TAG, "Cannot verify purchase: missing userId or productId")
            return
        }

        Thread {
            try {
                val url = URL("$BACKEND_URL/verify-google-play-purchase")
                val connection = url.openConnection() as HttpURLConnection

                connection.requestMethod = "POST"
                connection.setRequestProperty("Content-Type", "application/json")
                connection.doOutput = true

                val body = JSONObject()
                body.put("package_name", packageName)
                body.put("product_id", productId)
                body.put("purchase_token", purchase.purchaseToken)
                body.put("order_id", purchase.orderId)
                body.put("user_id", userId)
                body.put("workspace_id", pendingWorkspaceId ?: JSONObject.NULL)
                body.put("plan_type", planType)

                OutputStreamWriter(connection.outputStream).use { writer ->
                    writer.write(body.toString())
                    writer.flush()
                }

                val responseCode = connection.responseCode
                Log.d(TAG, "Backend verify response: $responseCode")

                connection.disconnect()

            } catch (e: Exception) {
                Log.e(TAG, "Backend verify error", e)
            }
        }.start()
    }
}