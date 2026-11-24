package uz.prava.prava_uz

import android.content.Intent
import android.media.AudioManager
import android.media.ToneGenerator
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.FileProvider
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File

/**
 * "uz.prava/updater" kanali: ilova ichidan yangilanish (Dart APK'ni cacheDir/updates/ ga yuklab oladi,
 * bu yerdan Android o'rnatish oynasi ochiladi — FileProvider orqali) va javob ovozi ("tone").
 */
class MainActivity : FlutterActivity() {
    private var tones: ToneGenerator? = null

    override fun onDestroy() {
        tones?.release()
        tones = null
        super.onDestroy()
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "uz.prava/updater").setMethodCallHandler { call, result ->
            when (call.method) {
                "versionCode" -> result.success(currentVersionCode())
                "versionName" -> result.success(packageManager.getPackageInfo(packageName, 0).versionName)
                // Javob ovozi (sozlamada yoqilgan bo'lsa): fayl/paketsiz, tizim ohanglari bilan
                "tone" -> {
                    val ok = call.argument<Boolean>("ok") ?: true
                    try {
                        val tg = tones ?: ToneGenerator(AudioManager.STREAM_MUSIC, 60).also { tones = it }
                        tg.startTone(if (ok) ToneGenerator.TONE_PROP_ACK else ToneGenerator.TONE_PROP_NACK, 180)
                    } catch (_: RuntimeException) {
                        // ba'zi qurilmalarda ToneGenerator yaratilmaydi — ovozsiz davom etamiz
                    }
                    result.success(null)
                }
                "updatesDir" -> {
                    val dir = File(cacheDir, "updates").apply { mkdirs() }
                    result.success(dir.absolutePath)
                }
                // Android 8+ da "noma'lum manbalardan o'rnatish" ruxsati ilova uchun alohida beriladi
                "canInstall" -> result.success(
                    Build.VERSION.SDK_INT < Build.VERSION_CODES.O || packageManager.canRequestPackageInstalls()
                )
                "openInstallSettings" -> {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        startActivity(
                            Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:$packageName"))
                        )
                    }
                    result.success(null)
                }
                "install" -> {
                    val path = call.argument<String>("path")
                    val file = path?.let { File(it) }
                    if (file == null || !file.exists()) {
                        result.error("NO_FILE", "APK topilmadi", null)
                    } else {
                        val uri = FileProvider.getUriForFile(this, "$packageName.updates", file)
                        val intent = Intent(Intent.ACTION_VIEW).apply {
                            setDataAndType(uri, "application/vnd.android.package-archive")
                            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
                        }
                        startActivity(intent)
                        result.success(null)
                    }
                }
                else -> result.notImplemented()
            }
        }
    }

    @Suppress("DEPRECATION")
    private fun currentVersionCode(): Long {
        val info = packageManager.getPackageInfo(packageName, 0)
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) info.longVersionCode else info.versionCode.toLong()
    }
}
