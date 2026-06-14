package com.example.vocabulary

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.livedata.observeAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import coil.compose.AsyncImage
import com.example.vocabulary.ui.theme.VocabularyTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            VocabularyTheme {
                MainScreen()
            }
        }
    }
}

sealed class Screen(val route: String, val title: String, val icon: ImageVector) {
    object Home : Screen("home", "Trang chủ", Icons.Default.Home)
    object Vocab : Screen("vocab", "Từ vựng", Icons.Default.List)
    object Study : Screen("study", "Ôn tập", Icons.Default.PlayArrow)
    object Stats : Screen("stats", "Thống kê", Icons.Default.BarChart)
}

@Composable
fun MainScreen() {
    val navController = rememberNavController()
    val viewModel: VocabViewModel = viewModel(
        factory = VocabViewModelFactory(LocalContext.current.applicationContext as android.app.Application)
    )

    Scaffold(
        bottomBar = { BottomNavigationBar(navController) }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = Screen.Home.route,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(Screen.Home.route) { HomeScreen(viewModel) }
            composable(Screen.Vocab.route) { VocabListScreen(viewModel) }
            composable(Screen.Study.route) { StudyScreen() }
            composable(Screen.Stats.route) { StatsScreen(viewModel) }
        }
    }
}

@Composable
fun BottomNavigationBar(navController: NavHostController) {
    val items = listOf(Screen.Home, Screen.Vocab, Screen.Study, Screen.Stats)
    NavigationBar(
        containerColor = MaterialTheme.colorScheme.surface,
        tonalElevation = 8.dp
    ) {
        val navBackStackEntry by navController.currentBackStackEntryAsState()
        val currentRoute = navBackStackEntry?.destination?.route
        items.forEach { screen ->
            NavigationBarItem(
                icon = { Icon(screen.icon, contentDescription = screen.title) },
                label = { Text(screen.title) },
                selected = currentRoute == screen.route,
                onClick = {
                    navController.navigate(screen.route) {
                        popUpTo(navController.graph.startDestinationId)
                        launchSingleTop = true
                    }
                }
            )
        }
    }
}

@Composable
fun HomeScreen(viewModel: VocabViewModel) {
    val totalReps by viewModel.totalStudyCount.collectAsState(initial = 0)
    var showAddDialog by remember { mutableStateOf(false) }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    colors = listOf(MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.2f), Color.Transparent)
                )
            )
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            val (treeIcon, treeMsg, color) = when {
                totalReps >= 500 -> Triple("🍎", "Khu rừng tri thức của bạn!", Color(0xFF059669))
                totalReps >= 150 -> Triple("🌳", "Cây đang phát triển mạnh mẽ!", Color(0xFF10B981))
                totalReps >= 30 -> Triple("🌿", "Mầm non đang vươn cao!", Color(0xFF4F46E5))
                else -> Triple("🌱", "Hãy bắt đầu gieo mầm ngay!", Color(0xFF6366F1))
            }

            Text(text = treeIcon, fontSize = 140.sp)
            Spacer(modifier = Modifier.height(24.dp))
            Text(
                text = treeMsg,
                fontSize = 26.sp,
                fontWeight = FontWeight.ExtraBold,
                color = color,
                textAlign = androidx.compose.ui.text.style.TextAlign.Center
            )
            Spacer(modifier = Modifier.height(12.dp))
            Surface(
                color = MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.5f),
                shape = RoundedCornerShape(24.dp)
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 20.dp, vertical = 10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(Icons.Default.WaterDrop, contentDescription = null, tint = Color(0xFF3B82F6), modifier = Modifier.size(20.dp))
                    Spacer(Modifier.width(8.dp))
                    Text(
                        text = "Điểm tích lũy: $totalReps",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                }
            }

            Spacer(modifier = Modifier.height(60.dp))
            Button(
                onClick = { showAddDialog = true },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(64.dp),
                shape = RoundedCornerShape(20.dp),
                elevation = ButtonDefaults.buttonElevation(defaultElevation = 4.dp)
            ) {
                Icon(Icons.Default.AutoFixHigh, contentDescription = null)
                Spacer(Modifier.width(12.dp))
                Text("Thêm từ tự động", fontSize = 20.sp, fontWeight = FontWeight.Bold)
            }
        }
    }

    if (showAddDialog) {
        AutoAddVocabDialog(
            viewModel = viewModel,
            onDismiss = { showAddDialog = false }
        )
    }
}

@Composable
fun AutoAddVocabDialog(viewModel: VocabViewModel, onDismiss: () -> Unit) {
    var word by remember { mutableStateOf("") }
    val isSearching by viewModel.isSearching.observeAsState(false)

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Thêm từ vựng thông minh", fontWeight = FontWeight.Bold) },
        text = {
            Column {
                Text("Nhập từ tiếng Anh, hệ thống sẽ tự động tìm nghĩa, ví dụ, phiên âm và ảnh minh họa.", style = MaterialTheme.typography.bodyMedium)
                Spacer(modifier = Modifier.height(16.dp))
                OutlinedTextField(
                    value = word,
                    onValueChange = { word = it },
                    label = { Text("Từ tiếng Anh") },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    singleLine = true,
                    enabled = !isSearching,
                    leadingIcon = { Icon(Icons.Default.Translate, contentDescription = null) }
                )
                if (isSearching) {
                    Spacer(modifier = Modifier.height(16.dp))
                    LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                }
            }
        },
        confirmButton = {
            Button(
                onClick = { 
                    if (word.isNotBlank()) {
                        viewModel.addVocabAutomated(word)
                        if (!isSearching) {
                            // We don't dismiss immediately because it's async, 
                            // but for better UX we can dismiss after start or wait for success
                            onDismiss() 
                        }
                    }
                },
                enabled = word.isNotBlank() && !isSearching,
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("Tìm & Lưu")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss, enabled = !isSearching) {
                Text("Hủy")
            }
        }
    )
}

@Composable
fun VocabListScreen(viewModel: VocabViewModel) {
    var selectedTab by remember { mutableIntStateOf(0) }
    val tabs = listOf("Từ Đơn", "Cụm Từ", "Ngữ Pháp")

    val vocabList by viewModel.allVocab.collectAsState(initial = emptyList())
    val phraseList by viewModel.allPhrases.collectAsState(initial = emptyList())
    val grammarList by viewModel.allGrammar.collectAsState(initial = emptyList())

    Column(modifier = Modifier.fillMaxSize()) {
        CenterAlignedTopAppBar(
            title = { Text("DANH SÁCH TỪ VỰNG", fontWeight = FontWeight.Black, fontSize = 20.sp) },
            colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                containerColor = MaterialTheme.colorScheme.surface
            )
        )
        
        SecondaryTabRow(selectedTabIndex = selectedTab) {
            tabs.forEachIndexed { index, title ->
                Tab(
                    selected = selectedTab == index,
                    onClick = { selectedTab = index },
                    text = { Text(title, fontWeight = if (selectedTab == index) FontWeight.Bold else FontWeight.Normal) }
                )
            }
        }

        val currentList = when (selectedTab) {
            0 -> vocabList
            1 -> phraseList
            else -> grammarList
        }

        ListContent(currentList, viewModel)
    }
}

@Composable
fun <T> ListContent(items: List<T>, viewModel: VocabViewModel) {
    if (items.isEmpty()) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Icon(Icons.Default.Inbox, contentDescription = null, size(64.dp), tint = Color.LightGray)
                Text("Chưa có từ nào", color = Color.Gray)
            }
        }
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        itemsIndexed(items) { index, item ->
            val vocabItem = when (item) {
                is VocabEntity -> item
                else -> null // Expand for others later
            }
            
            if (vocabItem != null) {
                VocabCard(vocabItem, viewModel, index)
            }
        }
    }
}

@Composable
fun VocabCard(item: VocabEntity, viewModel: VocabViewModel, index: Int) {
    var expanded by remember { mutableStateOf(false) }

    AnimatedVisibility(
        visible = true,
        enter = fadeIn() + slideInVertically(initialOffsetY = { 50 * (index + 1) })
    ) {
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .clickable { expanded = !expanded },
            shape = RoundedCornerShape(20.dp),
            colors = CardDefaults.cardColors(
                containerColor = if (expanded) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.3f) 
                                 else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f)
            ),
            elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (item.imageUrl.isNotBlank()) {
                        AsyncImage(
                            model = item.imageUrl,
                            contentDescription = null,
                            modifier = Modifier
                                .size(60.dp)
                                .clip(RoundedCornerShape(12.dp)),
                            contentScale = ContentScale.Crop
                        )
                        Spacer(Modifier.width(16.dp))
                    }
                    
                    Column(modifier = Modifier.weight(1f)) {
                        Text(item.word, fontWeight = FontWeight.ExtraBold, fontSize = 22.sp, color = MaterialTheme.colorScheme.onSurface)
                        if (item.phonetic.isNotBlank()) {
                            Text(item.phonetic, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary, fontStyle = FontStyle.Italic)
                        }
                    }

                    IconButton(
                        onClick = { viewModel.speak(item.word) },
                        modifier = Modifier.background(MaterialTheme.colorScheme.primary, CircleShape)
                    ) {
                        Icon(Icons.Default.VolumeUp, contentDescription = "Đọc", tint = Color.White)
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))
                Text(item.vnMeaning, fontWeight = FontWeight.Bold, fontSize = 18.sp, color = MaterialTheme.colorScheme.secondary)

                if (expanded) {
                    Spacer(modifier = Modifier.height(12.dp))
                    Divider(color = MaterialTheme.colorScheme.outlineVariant)
                    Spacer(modifier = Modifier.height(12.dp))
                    
                    if (item.sentence.isNotBlank()) {
                        Text("Ví dụ:", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.labelLarge)
                        Text(item.sentence, style = MaterialTheme.typography.bodyLarge, fontStyle = FontStyle.Italic)
                    }
                    
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                        TextButton(onClick = { viewModel.deleteVocab(item) }, colors = ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.error)) {
                            Icon(Icons.Default.Delete, contentDescription = null)
                            Text("Xóa")
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun StudyScreen() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(20.dp, Alignment.CenterVertically)
    ) {
        Text(
            "CHẾ ĐỘ ÔN TẬP",
            style = MaterialTheme.typography.headlineLarge,
            fontWeight = FontWeight.Black,
            color = MaterialTheme.colorScheme.primary
        )

        StudyCard("Học Flashcard", "Ghi nhớ từ vựng qua thẻ", Color(0xFF6366F1), Icons.Default.ViewCarousel) { }
        StudyCard("Trắc nghiệm", "Kiểm tra phản xạ nghĩa", Color(0xFF10B981), Icons.Default.Quiz) { }
        StudyCard("Nghe & Viết", "Luyện kỹ năng nghe", Color(0xFFF59E0B), Icons.Default.Hearing) { }
    }
}

@Composable
fun StudyCard(title: String, subtitle: String, color: Color, icon: ImageVector, onClick: () -> Unit) {
    ElevatedCard(
        onClick = onClick,
        modifier = Modifier
            .fillMaxWidth()
            .height(100.dp),
        shape = RoundedCornerShape(24.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxSize()
                .padding(20.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Surface(
                modifier = Modifier.size(56.dp),
                shape = RoundedCornerShape(16.dp),
                color = color.copy(alpha = 0.15f)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(28.dp))
                }
            }
            Spacer(Modifier.width(20.dp))
            Column {
                Text(title, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                Text(subtitle, fontSize = 14.sp, color = Color.Gray)
            }
        }
    }
}

@Composable
fun StatsScreen(viewModel: VocabViewModel) {
    val vocabList by viewModel.allVocab.collectAsState(initial = emptyList())

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp)
    ) {
        Text("THỐNG KÊ", style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Black)
        Spacer(Modifier.height(32.dp))

        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(24.dp)
        ) {
            Column(modifier = Modifier.padding(24.dp)) {
                StatRow("Số từ đã học", vocabList.size.toString())
                HorizontalDivider(modifier = Modifier.padding(vertical = 16.dp), color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
                StatRow("Đã thuộc (Mastered)", vocabList.count { it.isMastered }.toString())
                HorizontalDivider(modifier = Modifier.padding(vertical = 16.dp), color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
                StatRow("Tổng lượt ôn tập", vocabList.sumOf { it.studyCount }.toString())
            }
        }
    }
}

@Composable
fun StatRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, fontSize = 24.sp, fontWeight = FontWeight.Black, color = MaterialTheme.colorScheme.primary)
    }
}

// Utility extension for sizes
fun Modifier.size(size: androidx.compose.ui.unit.Dp) = this.then(Modifier.width(size).height(size))
