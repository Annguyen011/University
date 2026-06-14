package com.example.vocabulary

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Path

interface DictionaryApi {
    @GET("en/{word}")
    suspend fun getWordDefinition(@Path("word") word: String): List<WordDefinition>
}

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
    private const val BASE_URL = "https://api.dictionaryapi.dev/api/v2/entries/"

    val dictionaryApi: DictionaryApi by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(DictionaryApi::class.java)
    }
}
