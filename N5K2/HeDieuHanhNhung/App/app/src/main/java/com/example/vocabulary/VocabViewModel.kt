package com.example.vocabulary

import android.app.Application
import android.speech.tts.TextToSpeech
import androidx.lifecycle.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.*

class VocabViewModel(application: Application) : AndroidViewModel(application), TextToSpeech.OnInitListener {
    private val dao = AppDatabase.getDatabase(application).vocabDao()
    private var tts: TextToSpeech? = TextToSpeech(application, this)

    val allVocab: Flow<List<VocabEntity>> = dao.getAllVocab()
    val allPhrases: Flow<List<PhraseEntity>> = dao.getAllPhrases()
    val allGrammar: Flow<List<GrammarEntity>> = dao.getAllGrammar()

    private val _isSearching = MutableLiveData(false)
    val isSearching: LiveData<Boolean> = _isSearching

    private val _lastError = MutableLiveData<String?>(null)
    val lastError: LiveData<String?> = _lastError

    fun addVocab(word: String, vnMeaning: String, pos: String = "noun", sentence: String = "") {
        viewModelScope.launch {
            dao.insertVocab(VocabEntity(word, sentence, pos, vnMeaning))
        }
    }

    fun addVocabAutomated(inputWord: String) {
        viewModelScope.launch {
            _isSearching.value = true
            _lastError.value = null
            try {
                // 1. Spelling correction check
                val suggestions = withContext(Dispatchers.IO) {
                    RetrofitClient.spellingApi.getSpellingSuggestions(inputWord)
                }
                
                // Use the top suggestion if it has a high score and is different from input
                val correctedWord = if (suggestions.isNotEmpty() && suggestions[0].score > 500) {
                    suggestions[0].word
                } else {
                    inputWord
                }

                // 2. Fetch English definition and example
                val definitions = withContext(Dispatchers.IO) {
                    try {
                        RetrofitClient.dictionaryApi.getWordDefinition(correctedWord)
                    } catch (e: Exception) {
                        emptyList()
                    }
                }
                
                if (definitions.isNotEmpty()) {
                    val firstMatch = definitions[0]
                    val word = firstMatch.word
                    val phonetic = firstMatch.phonetic ?: ""
                    val meaningEn = firstMatch.meanings.firstOrNull()
                    val definitionEn = meaningEn?.definitions?.firstOrNull()
                    val example = definitionEn?.example ?: ""
                    val pos = meaningEn?.partOfSpeech ?: "noun"

                    // 3. Translate to Vietnamese
                    val translation = withContext(Dispatchers.IO) {
                        RetrofitClient.translationApi.translate(word)
                    }
                    val vnMeaning = translation.responseData.translatedText

                    // 4. Image URL using a keyword-based service
                    val imageUrl = "https://loremflickr.com/320/240/$word"

                    dao.insertVocab(
                        VocabEntity(
                            word = word,
                            sentence = example,
                            pos = pos,
                            vnMeaning = vnMeaning,
                            phonetic = phonetic,
                            imageUrl = imageUrl
                        )
                    )
                } else {
                    _lastError.value = "Không tìm thấy định nghĩa cho '$correctedWord'"
                }
            } catch (e: Exception) {
                e.printStackTrace()
                _lastError.value = "Lỗi kết nối. Vui lòng thử lại!"
            } finally {
                _isSearching.value = false
            }
        }
    }

    fun speak(text: String) {
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, null)
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            tts?.language = Locale.US
        }
    }

    override fun onCleared() {
        super.onCleared()
        tts?.stop()
        tts?.shutdown()
    }

    fun deleteVocab(vocab: VocabEntity) {
        viewModelScope.launch {
            dao.deleteVocab(vocab)
        }
    }

    val totalStudyCount: Flow<Int> = allVocab.map { list -> list.sumOf { it.studyCount } }
}

class VocabViewModelFactory(private val application: Application) : ViewModelProvider.Factory {
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(VocabViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return VocabViewModel(application) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class")
    }
}
