package com.example.vocabulary

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "vocab")
data class VocabEntity(
    @PrimaryKey val word: String,
    val sentence: String,
    val pos: String,
    val vnMeaning: String,
    val lastStudied: String = "",
    val studyCount: Int = 0,
    val customSentence: String = "",
    val itemType: String = "vocab",
    val isMastered: Boolean = false,
    val phonetic: String = "",
    val imageUrl: String = ""
)

@Entity(tableName = "phrase")
data class PhraseEntity(
    @PrimaryKey val word: String,
    val sentence: String,
    val pos: String,
    val vnMeaning: String,
    val lastStudied: String = "",
    val studyCount: Int = 0,
    val customSentence: String = "",
    val itemType: String = "phrase",
    val isMastered: Boolean = false,
    val phonetic: String = "",
    val imageUrl: String = ""
)

@Entity(tableName = "grammar")
data class GrammarEntity(
    @PrimaryKey val word: String,
    val sentence: String,
    val pos: String,
    val vnMeaning: String,
    val lastStudied: String = "",
    val studyCount: Int = 0,
    val customSentence: String = "",
    val itemType: String = "grammar",
    val isMastered: Boolean = false,
    val phonetic: String = "",
    val imageUrl: String = ""
)
