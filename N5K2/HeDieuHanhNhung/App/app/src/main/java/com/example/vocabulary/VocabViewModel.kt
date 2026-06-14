package com.example.vocabulary

import android.app.Application
import androidx.lifecycle.*
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

class VocabViewModel(application: Application) : AndroidViewModel(application) {
    private val dao = AppDatabase.getDatabase(application).vocabDao()

    val allVocab: Flow<List<VocabEntity>> = dao.getAllVocab()
    val allPhrases: Flow<List<PhraseEntity>> = dao.getAllPhrases()
    val allGrammar: Flow<List<GrammarEntity>> = dao.getAllGrammar()

    fun addVocab(word: String, vnMeaning: String, pos: String = "noun", sentence: String = "") {
        viewModelScope.launch {
            dao.insertVocab(VocabEntity(word, sentence, pos, vnMeaning))
        }
    }

    fun updateProgress(word: String) {
        viewModelScope.launch {
            val vocab = dao.getVocabByWord(word) ?: return@launch
            val now = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault()).format(Date())
            dao.updateVocab(vocab.copy(
                studyCount = vocab.studyCount + 1,
                lastStudied = now
            ))
        }
    }

    // Stats for the "Tree" logic
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
