package com.example.vocabulary

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

interface DictionaryApi {
    @GET("en/{word}")
    suspend fun getWordDefinition(@Path("word") word: String): List<WordDefinition>
}

interface TranslationApi {
    @GET("get")
    suspend fun translate(
        @Query("q") query: String,
        @Query("langpair") langPair: String = "en|vi"
    ): TranslationResponse
}

interface SpellingApi {
    @GET("words")
    suspend fun getSpellingSuggestions(
        @Query("sp") pattern: String,
        @Query("max") limit: Int = 1
    ): List<SpellingSuggestion>
}

data class SpellingSuggestion(val word: String, val score: Int)
data class TranslationResponse(val responseData: TranslationData)
data class TranslationData(val translatedText: String)

data class WordDefinition(
    val word: String,
    val phonetic: String?,
    val phonetics: List<Phonetic>,
    val meanings: List<Meaning>
)

data class Phonetic(val text: String?, val audio: String?)
data class Meaning(
    val partOfSpeech: String,
    val definitions: List<Definition>
)

data class Definition(
    val definition: String,
    val example: String?,
    val synonyms: List<String>,
    val antonyms: List<String>
)

object RetrofitClient {
    private const val DICTIONARY_BASE_URL = "https://api.dictionaryapi.dev/api/v2/entries/"
    private const val TRANSLATE_BASE_URL = "https://api.mymemory.translated.net/"
    private const val SPELl_BASE_URL = "https://api.datamuse.com/"

    val dictionaryApi: DictionaryApi by lazy {
        Retrofit.Builder()
            .baseUrl(DICTIONARY_BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(DictionaryApi::class.java)
    }

    val translationApi: TranslationApi by lazy {
        Retrofit.Builder()
            .baseUrl(TRANSLATE_BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(TranslationApi::class.java)
    }

    val spellingApi: SpellingApi by lazy {
        Retrofit.Builder()
            .baseUrl(SPELl_BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(SpellingApi::class.java)
    }
}
